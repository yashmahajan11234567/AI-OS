# Part13 Schema Reference: Governance Schemas

This document defines the technology-neutral governance data contracts for the AI-OS Multi-Agent Collaboration Architecture. 

All governance schemas adhere to the schema architecture specification defined in Part12, Sections 1-34. This document focuses exclusively on the governance-specific data contract definitions, referencing Part12 for all schema infrastructure including governance model, ownership, lifecycle, evolution, compatibility, validation, contract testing, registry, deprecation, and conformance requirements.

---

## Policy Schema

### Purpose
Defines the structure for governance policies that establish rules, standards, and guidelines for agent behavior, system operations, and organizational conduct within the AI-OS ecosystem.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `policyId` | string | Unique identifier for the policy (see Part 12 for UUID v4 definition) |
| `name` | string | Human-readable name for the policy |
| `version` | string | Semantic version of the policy (see Part 12 for semantic versioning rules) |
| `description` | string | Detailed description of the policy's purpose and scope |
| `policyType` | string | Type of policy (`data`, `data_handling`, `security`, `operational`, `ethical`, `compliance`) |
| `rules` | array[PolicyRule] | Ordered list of rules that constitute the policy |
| `scope` | string | Applicability scope (`global`, `system`, `workflow`, `agent_group`, `agent`) |
| `targetEntities` | array[string] | List of entity types or IDs the policy applies to (e.g., agentIds, workflow types) |
| `effectiveFrom` | string (ISO 8601) | Timestamp when the policy becomes effective (see Part 12 for ISO 8601 timestamp format) |
| `effectiveUntil` | string (ISO 8601) or null | Timestamp when the policy expires (see Part 12 for ISO 8601 timestamp format) |
| `enforcementLevel` | string | Enforcement strictness (`advisory`, `mandatory`, `blocking`) |
| `createdBy` | string | AgentId or userId that created the policy (see Part 12 for identifier formats) |
| `createdAt` | string (ISO 8601) | Timestamp when the policy was created (see Part 12 for ISO 8601 timestamp format) |
| `updatedAt` | string (ISO 8601) | Timestamp when the policy was last updated (see Part 12 for ISO 8601 timestamp format) |
| `tags` | array[string] | Tags for categorization and discovery (see Part 12 for tags field usage) |
| `metadata` | object | Arbitrary key-value pairs for policy-specific metadata (see Part 12 for metadata field usage) |

### PolicyRule Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `ruleId` | string | Unique identifier for the rule within the policy (see Part 12 for identifier formats) |
| `description` | string | Detailed description of what the rule mandates or prohibits |
| `condition` | string | Expression that must evaluate to true for the rule to apply (format depends on policy engine) |
| `effect` | string | The rule's effect when condition is met (`permit`, `deny`, `oblige`, `advise`, `transform`) |
| `obligations` | array[string] | Obligations that must be satisfied when the rule applies (e.g., `log`, `notify`, `annotate`, `require_step_up`) |
| `advice` | array[string] | Advisory recommendations when the rule applies (non-binding guidance) |
| `transformations` | array[string] | Transformations to apply to the request/context when the rule applies |
| `parameters` | object | Configuration parameters for the rule's effect and obligations (see Part 12 for parameters object usage) |
| `severity` | string | Impact severity if violated (`low`, `medium`, `high`, `critical`) |
| `exceptions` | array[PolicyException] | List of exceptions to this rule |

### Required Fields
- `policyId`
- `name`
- `version`
- `policyType`
- `rules`
- `scope`
- `effectiveFrom`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `targetEntities`
- `effectiveUntil`
- `enforcementLevel`
- `tags`
- `metadata`

### Validation Rules
#### Governance-Specific Validation
- `policyType` must be one of: `architecture`, `policy`, `agent`, `capability`, `workflow`, `data`, `knowledge`, `security`, `operational`, `risk`, `compliance`, `audit`
- `scope` must be one of: `global`, `system`, `workflow`, `agent_group`, `agent`
- Each rule in `rules` must have a unique `ruleId`
- `effect` must be one of: `permit`, `deny`, `oblige`, `advise`, `transform`
- `obligations` array items must be non-empty strings (common values: `log`, `notify`, `annotate`, `require_step_up`)
- `advice` array items must be non-empty strings
- `transformations` array items must be non-empty strings
- `severity` must be one of: `low`, `medium`, `high`, `critical`
- `enforcementLevel` if provided must be one of: `advisory`, `mandatory`, `blocking`

#### Infrastructure Validation (see Part 12)
- `policyId` must conform to the UUID v4 standard
- `version` must follow semantic versioning
- `effectiveFrom` must conform to the ISO 8601 timestamp format
- If `effectiveUntil` is provided, it must conform to the ISO 8601 timestamp format and be greater than `effectiveFrom`
- `createdBy` must conform to the agent/user identifier format
- `createdAt` and `updatedAt` must conform to the ISO 8601 timestamp format
- `updatedAt` must be greater than or equal to `createdAt`
- Each exception in `rules.exceptions` must conform to the PolicyException structure

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Policy",
  "type": "object",
  "required": ["policyId", "name", "version", "policyType", "rules", "scope", "effectiveFrom", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "policyId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "policyType": {
      "type": "string",
      "enum": ["architecture", "policy", "agent", "capability", "workflow", "data", "knowledge", "security", "operational", "risk", "compliance", "audit"]
    },
    "rules": {
      "type": "array",
      "items": { "$ref": "#/definitions/policyRule" },
      "minItems": 1
    },
    "scope": {
      "type": "string",
      "enum": ["global", "system", "workflow", "agent_group", "agent"]
    },
    "targetEntities": {
      "type": "array",
      "items": { "type": "string" }
    },
    "effectiveFrom": { "type": "string", "format": "date-time" },
    "effectiveUntil": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "enforcementLevel": {
      "type": "string",
      "enum": ["advisory", "mandatory", "blocking"]
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
    "policyRule": {
      "type": "object",
      "required": ["ruleId", "description", "condition", "effect", "severity"],
      "properties": {
        "ruleId": { "type": "string", "minLength": 1 },
        "description": { "type": "string" },
        "condition": { "type": "string" },
        "effect": {
          "type": "string",
          "enum": ["permit", "deny", "oblige", "advise", "transform"]
        },
        "obligations": {
          "type": "array",
          "items": { "type": "string", "minLength": 1 }
        },
        "advice": {
          "type": "array",
          "items": { "type": "string", "minLength": 1 }
        },
        "transformations": {
          "type": "array",
          "items": { "type": "string", "minLength": 1 }
        },
        "parameters": {
          "type": "object",
          "additionalProperties": true
        },
        "severity": {
          "type": "string",
          "enum": ["low", "medium", "high", "critical"]
        },
        "exceptions": {
          "type": "array",
          "items": { "$ref": "#/definitions/policyException" }
        }
      }
    },
    "policyException": {
      "type": "object",
      "required": ["exceptionId", "description", "condition"],
      "properties": {
        "exceptionId": { "type": "string", "minLength": 1 },
        "description": { "type": "string" },
        "condition": { "type": "string" },
        "justification": { "type": "string" },
        "grantedBy": {
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
        "grantedAt": { "type": "string", "format": "date-time" },
        "expiresAt": {
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
policyId: "123e4567-e89b-12d3-a456-426614174024"
name: "Data Access Control Policy"
version: "1.0.0"
description: "Policy governing access to sensitive data across AI-OS workflows"
policyType: "data"
rules:
  - ruleId: "rule-001"
    description: "Deny access to PII without explicit approval"
    condition: "dataClassification == 'PII'"
    effect: "deny"
    obligations:
      - "log"
      - "notify"
    severity: "high"
    exceptions:
      - exceptionId: "exp-001"
        description: "Approved research workflows may access anonymized PII"
        condition: "workflowType == 'research' and dataIsAnonymized == true"
        justification: "Research compliance framework"
        grantedBy: "governance-council"
        grantedAt: "2026-08-01T00:00:00Z"
        expiresAt: "2027-08-01T00:00:00Z"
  - ruleId: "rule-002"
    description: "Allow access to public data"
    condition: "dataClassification == 'public'"
    effect: "permit"
    obligations:
      - "log"
    severity: "low"
  - ruleId: "rule-003"
    description: "Obligate step-up authentication for sensitive data"
    condition: "dataClassification == 'confidential'"
    effect: "oblige"
    obligations:
      - "require_step_up"
      - "log"
    advice:
      - "Consider using hardware tokens for step-up"
    severity: "medium"
scope: "global"
targetEntities:
  - "workflow"
  - "agent"
effectiveFrom: "2026-08-01T00:00:00Z"
enforcementLevel: "mandatory"
createdBy: "123e4567-e89b-12d3-a456-426614174000"
createdAt: "2026-08-01T00:00:00Z"
updatedAt: "2026-08-07T09:00:00Z"
tags:
  - "data"
  - "privacy"
  - "access-control"
metadata:
  owner: "privacy-team"
  reviewCycleDays: 90
```

### Migration Rules
- When adding new policy types: Extend the `policyType` enum
- When changing rule structure: Provide backward compatibility for legacy rule formats
- **Note**: `action` field renamed to `effect` with canonical values (`permit`, `deny`, `oblige`, `advise`, `transform`); `obligations`, `advice`, and `transformations` arrays added per policies.md architecture
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by policy enforcement systems (Section 13.3)
- References Agent Schema for `createdBy` and `grantedBy` fields
- Related to Policy Evaluation Request/Result schemas for policy enforcement

---

## PolicySet Schema

### Purpose
Defines a collection of related policies that can be managed and evaluated as a unit, enabling policy composition and hierarchical governance structures.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `policySetId` | string | Unique identifier for the policy set (see Part 12 for UUID v4 definition) |
| `name` | string | Human-readable name for the policy set |
| `version` | string | Semantic version of the policy set (see Part 12 for semantic versioning rules) |
| `description` | string | Detailed description of the policy set's purpose and scope |
| `policyType` | string | Type of policies contained in this set (must be consistent across all policies) |
| `policies` | array[PolicyReference] | Ordered list of policy references that constitute the policy set |
| `scope` | string | Applicability scope (`global`, `system`, `workflow`, `agent_group`, `agent`) |
| `targetEntities` | array[string] | List of entity types or IDs the policy set applies to |
| `effectiveFrom` | string (ISO 8601) | Timestamp when the policy set becomes effective |
| `effectiveUntil` | string (ISO 8601) or null | Timestamp when the policy set expires |
| `conflictResolutionStrategy` | string | Strategy for resolving conflicts between policies (`deny_overrides`, `allow_overrides`, `ordered`, `required_all`, `deny_unless_permitted`) |
| `createdBy` | string | AgentId or userId that created the policy set |
| `createdAt` | string (ISO 8601) | Timestamp when the policy set was created |
| `updatedAt` | string (ISO 8601) | Timestamp when the policy set was last updated |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for policy set-specific metadata |

### PolicyReference Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `policyId` | string | Reference to a policy by its ID |
| `version` | string | Specific version of the policy to include (if omitted, latest version is used) |
| `weight` | number | Optional weight for weighted evaluation strategies (default: 1.0) |
| `overrideId` | string or null | Optional override identifier if this policy reference is subject to an override |

### Required Fields
- `policySetId`
- `name`
- `version`
- `policyType`
- `policies`
- `scope`
- `effectiveFrom`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `targetEntities`
- `effectiveUntil`
- `conflictResolutionStrategy`
- `tags`
- `metadata`

### Validation Rules
#### Governance-Specific Validation
- `policyType` must be one of: `architecture`, `policy`, `agent`, `capability`, `workflow`, `data`, `knowledge`, `security`, `operational`, `risk`, `compliance`, `audit`
- `scope` must be one of: `global`, `system`, `workflow`, `agent_group`, `agent`
- Each policy in `policies` must have a unique `policyId` within the set
- `conflictResolutionStrategy` if provided must be one of: `deny_overrides`, `allow_overrides`, `ordered`, `required_all`, `deny_unless_permitted`
- `weight` in policy references must be a positive number

#### Infrastructure Validation (see Part 12)
- `policySetId` must conform to the UUID v4 standard
- `version` must follow semantic versioning
- `effectiveFrom` must conform to the ISO 8601 timestamp format
- If `effectiveUntil` is provided, it must conform to the ISO 8601 timestamp format and be greater than `effectiveFrom`
- `createdBy` must conform to the agent/user identifier format
- `createdAt` and `updatedAt` must conform to the ISO 8601 timestamp format
- `updatedAt` must be greater than or equal to `createdAt`

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PolicySet",
  "type": "object",
  "required": ["policySetId", "name", "version", "policyType", "policies", "scope", "effectiveFrom", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "policySetId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "policyType": {
      "type": "string",
      "enum": ["architecture", "policy", "agent", "capability", "workflow", "data", "knowledge", "security", "operational", "risk", "compliance", "audit"]
    },
    "policies": {
      "type": "array",
      "items": { "$ref": "#/definitions/policyReference" },
      "minItems": 1
    },
    "scope": {
      "type": "string",
      "enum": ["global", "system", "workflow", "agent_group", "agent"]
    },
    "targetEntities": {
      "type": "array",
      "items": { "type": "string" }
    },
    "effectiveFrom": { "type": "string", "format": "date-time" },
    "effectiveUntil": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "conflictResolutionStrategy": {
      "type": "string",
      "enum": ["deny_overrides", "allow_overrides", "ordered", "required_all", "deny_unless_permitted"]
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
    "policyReference": {
      "type": "object",
      "required": ["policyId"],
      "properties": {
        "policyId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "version": {
          "type": "string",
          "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
        },
        "weight": {
          "type": "number",
          "minimum": 0
        },
        "overrideId": {
          "oneOf": [
            {
              "type": "string",
              "minLength": 1
            },
            {
              "type": "null"
            }
          ]
        }
      }
    }
  }
}
```

### YAML Example
```yaml
policySetId: "987f6543-e21b-43c5-b678-915525285135"
name: "Financial Services Policy Set"
version: "2.1.0"
description: "Collection of policies governing financial transactions and reporting"
policyType: "data"
policies:
  - policyId: "123e4567-e89b-12d3-a456-426614174024"
    version: "1.0.0"
    weight: 1.5
  - policyId: "123e4567-e89b-12d3-a456-426614174025"
    version: "1.2.0"
    weight: 1.0
scope: "system"
targetEntities:
  - "financial-workflow"
  - "audit-agent"
effectiveFrom: "2026-08-01T00:00:00Z"
conflictResolutionStrategy: "deny_overrides"
createdBy: "governance-system"
createdAt: "2026-08-01T00:00:00Z"
updatedAt: "2026-08-07T09:00:00Z"
tags:
  - "finance"
  - "compliance"
  - "data-handling"
metadata:
  owner: "finance-governance-team"
  reviewFrequency: "monthly"
```

### Migration Rules
- When adding new policy types: Extend the `policyType` enum
- When changing conflict resolution strategies: Maintain backward compatibility for existing strategy names
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by policy composition engines and hierarchical governance systems
- References Policy Schema for policy definitions
- Related to Policy Evaluation Request/Result schemas for batch policy evaluation

---

## Decision Schema

### Purpose
Defines the structure for governance decisions that record the outcomes of policy evaluations, including the reasoning, authorities involved, and resulting actions or directives.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `decisionId` | string | Unique identifier for the decision (see Part 12 for UUID v4 definition) |
| `name` | string | Human-readable name or title for the decision |
| `version` | string | Semantic version of the decision record (see Part 12 for semantic versioning rules) |
| `description` | string | Detailed description of the decision context and outcome |
| `decisionType` | string | Type of decision (`policy_approval`, `exception_grant`, `override_authorization`, `risk_acceptance`, `compliance_determination`, `audit_conclusion`) |
| `policyReferences` | array[PolicyReference] | List of policies that were evaluated to reach this decision |
| `subject` | string | Identifier of the entity or action the decision pertains to (agentId, workflowId, resourceId, etc.) |
| `subjectType` | string | Type of the subject (`agent`, `workflow`, `resource`, `data`, `knowledge`) |
| `outcome` | string | Result of the decision (`approved`, `denied`, `conditionally_approved`, `requires_review`, `escalated`) |
| `reasoning` | string | Detailed explanation of the reasoning behind the decision |
| `authorities` | array[AuthorityReference] | List of governing authorities that participated in or authorized the decision |
| `effectiveFrom` | string (ISO 8601) | Timestamp when the decision becomes effective |
| `effectiveUntil` | string (ISO 8601) or null | Timestamp when the decision expires |
| `createdBy` | string | AgentId or userId that initiated the decision process |
| `createdAt` | string (ISO 8601) | Timestamp when the decision was recorded |
| `updatedAt` | string (ISO 8601) | Timestamp when the decision was last updated |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for decision-specific metadata |

### PolicyReference Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `policyId` | string | Reference to a policy by its ID |
| `version` | string | Specific version of the policy that was evaluated |
| `evaluationResult` | string | Result of policy evaluation for this reference (`compliant`, `violated`, `not_applicable`) |
| `violatedRules` | array[string] | List of ruleIds that were violated (if evaluationResult is 'violated') |

### AuthorityReference Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `authorityId` | string | Reference to an authority by its ID |
| `authorityType` | string | Type of authority (`role_based`, `delegated`, `expertise`, `organizational`) |
| `role` | string | Specific role or capacity in which the authority participated |
| `vote` | string | Authority's vote or position (`approve`, `deny`, `abstain`, `condition`) |
| `conditions` | array[string] | List of conditions attached to the authority's vote (if any) |

### Required Fields
- `decisionId`
- `name`
- `version`
- `decisionType`
- `policyReferences`
- `subject`
- `subjectType`
- `outcome`
- `reasoning`
- `authorities`
- `effectiveFrom`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `effectiveUntil`
- `tags`
- `metadata`

### Validation Rules
#### Governance-Specific Validation
- `decisionType` must be one of: `policy_approval`, `exception_grant`, `override_authorization`, `risk_acceptance`, `compliance_determination`, `audit_conclusion`
- `subjectType` must be one of: `agent`, `workflow`, `resource`, `data`, `knowledge`
- `outcome` must be one of: `approved`, `denied`, `conditionally_approved`, `requires_review`, `escalated`
- Each policy in `policyReferences` must have a unique combination of `policyId` and `version`
- Each authority in `authorities` must have a unique `authorityId`
- `vote` in authority references must be one of: `approve`, `deny`, `abstain`, `condition`

#### Infrastructure Validation (see Part 12)
- `decisionId` must conform to the UUID v4 standard
- `version` must follow semantic versioning
- `effectiveFrom` must conform to the ISO 8601 timestamp format
- If `effectiveUntil` is provided, it must conform to the ISO 8601 timestamp format and be greater than `effectiveFrom`
- `createdBy` must conform to the agent/user identifier format
- `createdAt` and `updatedAt` must conform to the ISO 8601 timestamp format
- `updatedAt` must be greater than or equal to `createdAt`

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Decision",
  "type": "object",
  "required": ["decisionId", "name", "version", "decisionType", "policyReferences", "subject", "subjectType", "outcome", "reasoning", "authorities", "effectiveFrom", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "decisionId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "decisionType": {
      "type": "string",
      "enum": ["policy_approval", "exception_grant", "override_authorization", "risk_acceptance", "compliance_determination", "audit_conclusion"]
    },
    "policyReferences": {
      "type": "array",
      "items": { "$ref": "#/definitions/policyReference" },
      "minItems": 1
    },
    "subject": { "type": "string", "minLength": 1 },
    "subjectType": {
      "type": "string",
      "enum": ["agent", "workflow", "resource", "data", "knowledge"]
    },
    "outcome": {
      "type": "string",
      "enum": ["approved", "denied", "conditionally_approved", "requires_review", "escalated"]
    },
    "reasoning": { "type": "string" },
    "authorities": {
      "type": "array",
      "items": { "$ref": "#/definitions/authorityReference" },
      "minItems": 1
    },
    "effectiveFrom": { "type": "string", "format": "date-time" },
    "effectiveUntil": {
      "type": ["string", "null"],
      "format": "date-time"
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
    "policyReference": {
      "type": "object",
      "required": ["policyId", "version", "evaluationResult"],
      "properties": {
        "policyId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "version": {
          "type": "string",
          "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
        },
        "evaluationResult": {
          "type": "string",
          "enum": ["compliant", "violated", "not_applicable"]
        },
        "violatedRules": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "authorityReference": {
      "type": "object",
      "required": ["authorityId", "authorityType", "role", "vote"],
      "properties": {
        "authorityId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "authorityType": {
          "type": "string",
          "enum": ["role_based", "delegated", "expertise", "organizational"]
        },
        "role": { "type": "string", "minLength": 1 },
        "vote": {
          "type": "string",
          "enum": ["approve", "deny", "abstain", "condition"]
        },
        "conditions": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    }
  }
}
```

### YAML Example
```yaml
decisionId: "550e8400-e29b-41d4-a716-446655440000"
name: "PII Access Approval for Research Project Alpha"
version: "1.0.0"
description: "Decision granting conditional access to anonymized PII for medical research"
decisionType: "exception_grant"
policyReferences:
  - policyId: "123e4567-e89b-12d3-a456-426614174024"
    version: "1.0.0"
    evaluationResult: "violated"
    violatedRules:
      - "rule-001"
subject: "workflow-research-alpha-001"
subjectType: "workflow"
outcome: "conditionally_approved"
reasoning: "The research workflow demonstrates adequate anonymization techniques and operates under strict oversight, warranting an exception to the standard PII access prohibition."
authorities:
  - authorityId: "gov-council-chair-001"
    authorityType: "role_based"
    role: "Governance Council Chair"
    vote: "approve"
    conditions: ["annual re-evaluation required", "audit logs must be retained for 7 years"]
  - authorityId: "privacy-officer-002"
    authorityType: "role_based"
    role: "Chief Privacy Officer"
    vote: "approve"
    conditions: ["data minimization principles must be applied"]
effectiveFrom: "2026-08-01T00:00:00Z"
effectiveUntil: "2027-08-01T00:00:00Z"
createdBy: "governance-system"
createdAt: "2026-08-01T00:00:00Z"
updatedAt: "2026-08-01T00:00:00Z"
tags:
  - "pii"
  - "research"
  - "exception"
metadata:
  reviewDate: "2027-07-01T00:00:00Z"
  conditionsMet: false
```

### Migration Rules
- When adding new decision types: Extend the `decisionType` enum
- When adding new subject types: Extend the `subjectType` enum
- When adding new outcome types: Extend the `outcome` enum
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by decision recording systems and audit trails
- References Policy Schema for evaluated policies
- References Authority Schema for governing authorities
- Related to Policy Evaluation Request/Result schemas for decision inputs
- Used by compliance monitoring systems for decision enforcement tracking

---

## Authority Schema

### Purpose
Defines the structure for governance authorities that establish the rights, responsibilities, and accountabilities for making decisions, enforcing policies, and governing agent behavior within the AI-OS ecosystem.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `authorityId` | string | Unique identifier for the authority (see Part 12 for UUID v4 definition) |
| `name` | string | Human-readable name for the authority |
| `version` | string | Semantic version of the authority record (see Part 12 for semantic versioning rules) |
| `description` | string | Detailed description of the authority's scope and responsibilities |
| `authorityType` | string | Type of authority (`role_based`, `delegated`, `expertise`, `organizational`, `derived`) |
| `scope` | string | Applicability scope (`global`, `system`, `workflow`, `agent_group`, `agent`) |
| `domain` | string | Governance domain this authority operates in (see Part 13 context for domain definitions) |
| `responsibilities` | array[string] | List of specific responsibilities granted by this authority |
| `limitations` | array[string] | List of limitations or constraints on this authority |
| `delegatedFrom` | string or null | Identifier of the authority from which this authority was delegated (if applicable) |
| `delegationDepth` | integer | Depth of delegation chain (0 for original authority, 1 for first delegation, etc.) |
| `maxDelegationDepth` | integer | Maximum allowed depth for further delegation from this authority |
| `effectiveFrom` | string (ISO 8601) | Timestamp when the authority becomes effective |
| `effectiveUntil` | string (ISO 8601) or null | Timestamp when the authority expires |
| `createdBy` | string | AgentId or userId that established the authority |
| `createdAt` | string (ISO 8601) | Timestamp when the authority was established |
| `updatedAt` | string (ISO 8601) | Timestamp when the authority was last updated |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for authority-specific metadata |

### Required Fields
- `authorityId`
- `name`
- `version`
- `authorityType`
- `scope`
- `domain`
- `effectiveFrom`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `responsibilities`
- `limitations`
- `delegatedFrom`
- `delegationDepth`
- `maxDelegationDepth`
- `effectiveUntil`
- `tags`
- `metadata`

### Validation Rules
#### Governance-Specific Validation
- `authorityType` must be one of: `role_based`, `delegated`, `expertise`, `organizational`, `derived`
- `scope` must be one of: `global`, `system`, `workflow`, `agent_group`, `agent`
- `domain` must be a valid governance domain (refer to Part 13 context for domain definitions)
- `delegationDepth` must be a non-negative integer
- `maxDelegationDepth` must be a non-negative integer greater than or equal to `delegationDepth`
- If `delegatedFrom` is provided, `delegationDepth` must be greater than 0
- If `delegatedFrom` is null, `delegationDepth` must be 0

#### Infrastructure Validation (see Part 12)
- `authorityId` must conform to the UUID v4 standard
- `version` must follow semantic versioning
- `effectiveFrom` must conform to the ISO 8601 timestamp format
- If `effectiveUntil` is provided, it must conform to the ISO 8601 timestamp format and be greater than `effectiveFrom`
- `createdBy` must conform to the agent/user identifier format
- `createdAt` and `updatedAt` must conform to the ISO 8601 timestamp format
- `updatedAt` must be greater than or equal to `createdAt`

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Authority",
  "type": "object",
  "required": ["authorityId", "name", "version", "authorityType", "scope", "domain", "effectiveFrom", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "authorityId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "authorityType": {
      "type": "string",
      "enum": ["role_based", "delegated", "expertise", "organizational", "derived"]
    },
    "scope": {
      "type": "string",
      "enum": ["global", "system", "workflow", "agent_group", "agent"]
    },
    "domain": { "type": "string", "minLength": 1 },
    "responsibilities": {
      "type": "array",
      "items": { "type": "string" }
    },
    "limitations": {
      "type": "array",
      "items": { "type": "string" }
    },
    "delegatedFrom": {
      "oneOf": [
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "null"
        }
      ]
    },
    "delegationDepth": {
      "type": "integer",
      "minimum": 0
    },
    "maxDelegationDepth": {
      "type": "integer",
      "minimum": 0
    },
    "effectiveFrom": { "type": "string", "format": "date-time" },
    "effectiveUntil": {
      "type": ["string", "null"],
      "format": "date-time"
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
authorityId: "333e4567-e89b-12d3-a456-426614174050"
name: "Financial Transaction Approval Authority"
version: "1.0.0"
description: "Authority to approve financial transactions above certain thresholds"
authorityType: "role_based"
scope: "system"
domain: "financial-governance"
responsibilities:
  - "approve financial transactions up to $1,000,000"
  - "review and flag suspicious transaction patterns"
limitations:
  - "cannot approve transactions involving related parties without additional review"
  - "must escalate transactions over $5,000,000 to executive authority"
delegatedFrom: null
delegationDepth: 0
maxDelegationDepth: 2
effectiveFrom: "2026-08-01T00:00:00Z"
createdBy: "governance-system"
createdAt: "2026-08-01T00:00:00Z"
updatedAt: "2026-08-01T00:00:00Z"
tags:
  - "finance"
  - "approval"
  - "authority"
metadata:
  transactionLimit: 1000000
  reviewFrequency: "daily"
```

### Migration Rules
- When adding new authority types: Extend the `authorityType` enum
- When adding new governance domains: Update domain validation to include new domains
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by authorization systems and access control engines
- References Delegation Schema for delegation relationships
- Related to Decision Schema for recording authority participation in decisions
- Used by audit systems for tracking authority exercise and compliance

---

## Capability Schema

### Purpose
Defines the structure for governance capabilities that represent discrete operational abilities agents can exercise. Capabilities are the fundamental units of agent operational authority within the AI-OS ecosystem.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `capabilityId` | string | Unique identifier for the capability (see Part 12 for UUID v4 definition) |
| `name` | string | Human-readable name for the capability |
| `version` | string | Semantic version of the capability (see Part 12 for semantic versioning rules) |
| `description` | string | Detailed description of what the capability enables |
| `category` | string | Capability category (`data_access`, `model_execution`, `system_operation`, `configuration`, `administration`, `specialized`) |
| `scope` | string | Applicability scope (`global`, `system`, `workflow`, `agent_group`, `agent`) |
| `requiredApprovals` | array[string] | List of approval requirement identifiers for capability issuance |
| `riskLevel` | string | Risk level of the capability (`low`, `medium`, `high`, `critical`) |
| `constraints` | array[string] | Usage constraints and limitations on the capability |
| `dependencies` | array[string] | List of capability IDs that are required dependencies |
| `effectiveFrom` | string (ISO 8601) | Timestamp when the capability becomes effective |
| `effectiveUntil` | string (ISO 8601) or null | Timestamp when the capability expires |
| `createdBy` | string | Principal that defined the capability (agentId or userId) |
| `createdAt` | string (ISO 8601) | Creation timestamp |
| `updatedAt` | string (ISO 8601) | Last update timestamp |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for capability-specific metadata |

### Required Fields
- `capabilityId`
- `name`
- `version`
- `category`
- `scope`
- `riskLevel`
- `effectiveFrom`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `requiredApprovals`
- `constraints`
- `dependencies`
- `effectiveUntil`
- `tags`
- `metadata`

### Validation Rules
#### Governance-Specific Validation
- `category` must be one of: `data_access`, `model_execution`, `system_operation`, `configuration`, `administration`, `specialized`
- `scope` must be one of: `global`, `system`, `workflow`, `agent_group`, `agent`
- `riskLevel` must be one of: `low`, `medium`, `high`, `critical`
- Each item in `requiredApprovals` must be a non-empty string
- Each item in `constraints` must be a non-empty string
- Each item in `dependencies` must reference a valid `capabilityId`
- If `effectiveUntil` is provided, it must be greater than `effectiveFrom`

#### Infrastructure Validation (see Part 12)
- `capabilityId` must conform to the UUID v4 standard
- `version` must follow semantic versioning
- `effectiveFrom` must conform to the ISO 8601 timestamp format
- If `effectiveUntil` is provided, it must conform to the ISO 8601 timestamp format and be greater than `effectiveFrom`
- `createdBy` must conform to the agent/user identifier format
- `createdAt` and `updatedAt` must conform to the ISO 8601 timestamp format
- `updatedAt` must be greater than or equal to `createdAt`

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Capability",
  "type": "object",
  "required": ["capabilityId", "name", "version", "category", "scope", "riskLevel", "effectiveFrom", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "capabilityId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "category": {
      "type": "string",
      "enum": ["data_access", "model_execution", "system_operation", "configuration", "administration", "specialized"]
    },
    "scope": {
      "type": "string",
      "enum": ["global", "system", "workflow", "agent_group", "agent"]
    },
    "requiredApprovals": {
      "type": "array",
      "items": { "type": "string", "minLength": 1 }
    },
    "riskLevel": {
      "type": "string",
      "enum": ["low", "medium", "high", "critical"]
    },
    "constraints": {
      "type": "array",
      "items": { "type": "string", "minLength": 1 }
    },
    "dependencies": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
      }
    },
    "effectiveFrom": {
      "type": "string",
      "format": "date-time"
    },
    "effectiveUntil": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "createdBy": { "type": "string", "minLength": 1 },
    "createdAt": { "type": "string", "format": "date-time" },
    "updatedAt": { "type": "string", "format": "date-time" },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "metadata": { "type": "object" }
  }
}
```

### YAML Example
```yaml
capabilityId: "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
name: "ModelDeployment"
version: "1.0.0"
description: "Capability to deploy and manage ML model serving endpoints"
category: "model_execution"
scope: "system"
requiredApprovals: ["approval.model.deploy"]
riskLevel: "high"
constraints:
  - "max_models_per_endpoint: 5"
  - "required_monitoring: true"
  - "deployment_window: business_hours"
dependencies:
  - "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e"
effectiveFrom: "2026-08-01T00:00:00Z"
effectiveUntil: "2027-08-01T00:00:00Z"
createdBy: "governance-council-lead"
createdAt: "2026-07-15T10:30:00Z"
updatedAt: "2026-07-15T10:30:00Z"
tags: ["ml", "deployment", "production"]
metadata:
  charter: "ML Operations Governance Charter v2.1"
  reviewCycle: "quarterly"
```

### Migration Rules
- When adding new capability categories: Extend the `category` enum
- When adding new capability scopes: Extend the `scope` enum
- When adding new risk levels: Extend the `riskLevel` enum
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by capability management systems and agent provisioning services
- References Authority Schema for capability grants and authority bindings
- References Delegation Schema for delegated capability usage
- Used by audit systems for capability issuance and usage tracking
- Used by policy evaluation for capability-based access decisions
- Used by compliance systems for capability risk assessments

---

## Delegation Schema

### Purpose
Defines the structure for recording delegations of authority from one entity to another, including the scope, limitations, and duration of the delegation.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `delegationId` | string | Unique identifier for the delegation (see Part 12 for UUID v4 definition) |
| `name` | string | Human-readable name for the delegation |
| `version` | string | Semantic version of the delegation record (see Part 12 for semantic versioning rules) |
| `description` | string | Detailed description of the delegation's purpose and scope |
| `delegatorId` | string | Identifier of the entity delegating authority (agentId, authorityId, governanceBodyId) |
| `delegatorType` | string | Type of the delegator (`agent`, `authority`, `governance_body`, `role`) |
| `delegateeId` | string | Identifier of the entity receiving delegated authority (agentId, authorityId, roleId) |
| `delegateeType` | string | Type of the delegatee (`agent`, `authority`, `governance_body`, `role`) |
| `authorityId` | string | Identifier of the specific authority being delegated |
| `scope` | string | Applicability scope of the delegation (`global`, `system`, `workflow`, `agent_group`, `agent`) |
| `limitations` | array[string] | List of specific limitations or constraints on the delegated authority |
| `effectiveFrom` | string (ISO 8601) | Timestamp when the delegation becomes effective |
| `effectiveUntil` | string (ISO 8601) or null | Timestamp when the delegation expires |
| `createdBy` | string | AgentId or userId that created the delegation record |
| `createdAt` | string (ISO 8601) | Timestamp when the delegation was recorded |
| `updatedAt` | string (ISO 8601) | Timestamp when the delegation was last updated |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for delegation-specific metadata |

### Required Fields
- `delegationId`
- `name`
- `version`
- `delegatorId`
- `delegatorType`
- `delegateeId`
- `delegateeType`
- `authorityId`
- `scope`
- `effectiveFrom`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `limitations`
- `effectiveUntil`
- `tags`
- `metadata`

### Validation Rules
#### Governance-Specific Validation
- `delegatorType` must be one of: `agent`, `authority`, `governance_body`, `role`
- `delegateeType` must be one of: `agent`, `authority`, `governance_body`, `role`
- `scope` must be one of: `global`, `system`, `workflow`, `agent_group`, `agent`
- `authorityId` must reference a valid authority
- If `effectiveUntil` is provided, it must be greater than `effectiveFrom`

#### Infrastructure Validation (see Part 12)
- `delegationId` must conform to the UUID v4 standard
- `version` must follow semantic versioning
- `effectiveFrom` must conform to the ISO 8601 timestamp format
- If `effectiveUntil` is provided, it must conform to the ISO 8601 timestamp format and be greater than `effectiveFrom`
- `createdBy` must conform to the agent/user identifier format
- `createdAt` and `updatedAt` must conform to the ISO 8601 timestamp format
- `updatedAt` must be greater than or equal to `createdAt`

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Delegation",
  "type": "object",
  "required": ["delegationId", "name", "version", "delegatorId", "delegatorType", "delegateeId", "delegateeType", "authorityId", "scope", "effectiveFrom", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "delegationId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "delegatorId": { "type": "string", "minLength": 1 },
    "delegatorType": {
      "type": "string",
      "enum": ["agent", "authority", "governance_body", "role"]
    },
    "delegateeId": { "type": "string", "minLength": 1 },
    "delegateeType": {
      "type": "string",
      "enum": ["agent", "authority", "governance_body", "role"]
    },
    "authorityId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "scope": {
      "type": "string",
      "enum": ["global", "system", "workflow", "agent_group", "agent"]
    },
    "limitations": {
      "type": "array",
      "items": { "type": "string" }
    },
    "effectiveFrom": { "type": "string", "format": "date-time" },
    "effectiveUntil": {
      "type": ["string", "null"],
      "format": "date-time"
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
delegationId: "777e4567-e89b-12d3-a456-426614174070"
name: "Weekend Financial Approval Delegation"
version: "1.0.0"
description: "Delegation of financial approval authority for weekend operations"
delegatorId: "333e4567-e89b-12d3-a456-426614174050"
delegatorType: "authority"
delegateeId: "agent-weekend-approver-001"
delegateeType: "agent"
authorityId: "333e4567-e89b-12d3-a456-426614174050"
scope: "system"
limitations:
  - "only applicable Saturday and Sunday"
  - "transaction limit reduced to $100,000"
  - "must notify delegator of all approvals"
effectiveFrom: "2026-08-01T00:00:00Z"
effectiveUntil: "2026-09-01T00:00:00Z"
createdBy: "governance-system"
createdAt: "2026-08-01T00:00:00Z"
updatedAt: "2026-08-01T00:00:00Z"
tags:
  - "delegation"
  - "weekend"
  - "finance"
metadata:
  delegatorName: "Financial Transaction Approval Authority"
  delegateeName: "Weekend Approval Agent"
```

### Migration Rules
- When adding new delegator/delegatee types: Extend the respective enums
- When adding new scope values: Extend the scope enum
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by delegation management systems and access control engines
- References Authority Schema for authority definitions
- Related to Decision Schema for recording decisions made under delegated authority
- Used by audit systems for tracking delegation exercise and compliance
- Used by revocation systems for managing delegation lifecycle

---

## Approval Schema

### Purpose
Defines the structure for recording approvals of governance actions, decisions, or requests, including the approving authority, conditions, and temporal constraints.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `approvalId` | string | Unique identifier for the approval (see Part 12 for UUID v4 definition) |
| `name` | string | Human-readable name for the approval |
| `version` | string | Semantic version of the approval record (see Part 12 for semantic versioning rules) |
| `description` | string | Detailed description of what is being approved |
| `approvalType` | string | Type of approval (`policy`, `decision`, `delegation`, `exception`, `override`, `audit_finding`, `risk_assessment`) |
| `approvedEntityId` | string | Identifier of the entity being approved (policyId, decisionId, delegationId, etc.) |
| `approvedEntityType` | string | Type of the entity being approved (`policy`, `decision`, `delegation`, `exception`, `override`, `audit_finding`, `risk_assessment`) |
| `approverId` | string | Identifier of the approving authority or agent |
| `approverType` | string | Type of the approver (`authority`, `agent`, `governance_body`, `role`) |
| `approvalDecision` | string | The approval decision (`approved`, `denied`, `conditionally_approved`) |
| `conditions` | array[string] | List of conditions attached to the approval (if any) |
| `justification` | string | Reasoning or justification for the approval decision |
| `effectiveFrom` | string (ISO 8601) | Timestamp when the approval becomes effective |
| `effectiveUntil` | string (ISO 8601) or null | Timestamp when the approval expires |
| `createdBy` | string | AgentId or userId that created the approval record |
| `createdAt` | string (ISO 8601) | Timestamp when the approval was recorded |
| `updatedAt` | string (ISO 8601) | Timestamp when the approval was last updated |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for approval-specific metadata |

### Required Fields
- `approvalId`
- `name`
- `version`
- `approvalType`
- `approvedEntityId`
- `approvedEntityType`
- `approverId`
- `approverType`
- `approvalDecision`
- `justification`
- `effectiveFrom`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `conditions`
- `effectiveUntil`
- `tags`
- `metadata`

### Validation Rules
#### Governance-Specific Validation
- `approvalType` must be one of: `policy`, `decision`, `delegation`, `exception`, `override`, `audit_finding`, `risk_assessment`
- `approvedEntityType` must be one of: `policy`, `decision`, `delegation`, `exception`, `override`, `audit_finding`, `risk_assessment`
- `approverType` must be one of: `authority`, `agent`, `governance_body`, `role`
- `approvalDecision` must be one of: `approved`, `denied`, `conditionally_approved`
- If `approvalDecision` is `conditionally_approved`, `conditions` must not be empty
- If `effectiveUntil` is provided, it must be greater than `effectiveFrom`

#### Infrastructure Validation (see Part 12)
- `approvalId` must conform to the UUID v4 standard
- `version` must follow semantic versioning
- `effectiveFrom` must conform to the ISO 8601 timestamp format
- If `effectiveUntil` is provided, it must conform to the ISO 8601 timestamp format and be greater than `effectiveFrom`
- `createdBy` must conform to the agent/user identifier format
- `createdAt` and `updatedAt` must conform to the ISO 8601 timestamp format
- `updatedAt` must be greater than or equal to `createdAt`

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Approval",
  "type": "object",
  "required": ["approvalId", "name", "version", "approvalType", "approvedEntityId", "approvedEntityType", "approverId", "approverType", "approvalDecision", "justification", "effectiveFrom", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "approvalId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "approvalType": {
      "type": "string",
      "enum": ["policy", "decision", "delegation", "exception", "override", "audit_finding", "risk_assessment"]
    },
    "approvedEntityId": { "type": "string", "minLength": 1 },
    "approvedEntityType": {
      "type": "string",
      "enum": ["policy", "decision", "delegation", "exception", "override", "audit_finding", "risk_assessment"]
    },
    "approverId": { "type": "string", "minLength": 1 },
    "approverType": {
      "type": "string",
      "enum": ["authority", "agent", "governance_body", "role"]
    },
    "approvalDecision": {
      "type": "string",
      "enum": ["approved", "denied", "conditionally_approved"]
    },
    "conditions": {
      "type": "array",
      "items": { "type": "string" }
    },
    "justification": { "type": "string" },
    "effectiveFrom": { "type": "string", "format": "date-time" },
    "effectiveUntil": {
      "type": ["string", "null"],
      "format": "date-time"
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
approvalId: "111e4567-e89b-12d3-a456-426614174090"
name: "Weekend Financial Approval Authorization"
version: "1.0.0"
description: "Approval for weekend financial transaction delegation"
approvalType: "delegation"
approvedEntityId: "777e4567-e89b-12d3-a456-426614174070"
approvedEntityType: "delegation"
approverId: "333e4567-e89b-12d3-a456-426614174050"
approverType: "authority"
approvalDecision: "approved"
conditions:
  - "Must provide daily summary of transactions"
  - "All transactions must be logged for audit"
justification: "Weekend operations require streamlined approval process with appropriate controls"
effectiveFrom: "2026-08-01T00:00:00Z"
effectiveUntil: "2026-09-01T00:00:00Z"
createdBy: "governance-system"
createdAt: "2026-08-01T00:00:00Z"
updatedAt: "2026-08-01T00:00:00Z"
tags:
  - "approval"
  - "delegation"
  - "weekend"
metadata:
  approverName: "Financial Transaction Approval Authority"
  delegateeName: "Weekend Approval Agent"
```

### Migration Rules
- When adding new approval types: Extend the `approvalType` enum
- When adding new entity types: Extend the `approvedEntityType` and `approverType` enums
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by approval workflow systems and access control engines
- References Delegation, Decision, Policy, and other schemas for approved entities
- References Authority Schema for approver definitions
- Related to Decision Schema for recording approvals as governance decisions
- Used by audit systems for tracking approval exercise and compliance

---

## Risk Schema

### Purpose
Defines the structure for recording and managing governance risks, including risk identification, assessment, mitigation strategies, and monitoring.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `riskId` | string | Unique identifier for the risk (see Part 12 for UUID v4 definition) |
| `name` | string | Human-readable name for the risk |
| `version` | string | Semantic version of the risk record (see Part 12 for semantic versioning rules) |
| `description` | string | Detailed description of the risk, its causes, and potential impacts |
| `riskType` | string | Type of risk (`operational`, `security`, `compliance`, `strategic`, `financial`, `reputational`) |
| `category` | string | Risk category within the type (e.g., for security: `data_breach`, `unauthorized_access`) |
| `likelihood` | string | Assessed likelihood of occurrence (`rare`, `unlikely`, `possible`, `likely`, `almost_certain`) |
| `impact` | string | Assessed impact if the risk occurs (`insignificant`, `minor`, `moderate`, `major`, `catastrophic`) |
| `riskScore` | number | Calculated risk score (typically likelihood × impact on a 1-25 scale) |
| `riskOwner` | string | Identifier of the entity responsible for managing the risk |
| `riskOwnerType` | string | Type of the risk owner (`agent`, `authority`, `governance_body`, `role`, `team`) |
| `mitigationStrategies` | array[MitigationStrategy] | List of strategies to reduce likelihood or impact |
| `existingControls` | array[ControlReference] | List of controls currently in place to manage the risk |
| `effectiveFrom` | string (ISO 8601) | Timestamp when the risk assessment becomes effective |
| `effectiveUntil` | string (ISO 8601) or null | Timestamp when the risk assessment expires |
| `createdBy` | string | AgentId or userId that identified or assessed the risk |
| `createdAt` | string (ISO 8601) | Timestamp when the risk was first recorded |
| `updatedAt` | string (ISO 8601) | Timestamp when the risk record was last updated |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for risk-specific metadata |

### MitigationStrategy Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `strategyId` | string | Unique identifier for the mitigation strategy |
| `description` | string | Detailed description of the mitigation strategy |
| `type` | string | Type of mitigation (`preventive`, `detective`, `corrective`, `compensating`) |
| `effectiveness` | string | Estimated effectiveness (`low`, `medium`, `high`) |
| `implementationStatus` | string | Status of implementation (`planned`, `in_progress`, `implemented`, `failed`) |
| `resourcesRequired` | object | Resources needed to implement the strategy (personnel, budget, tools) |
| `targetCompletionDate` | string (ISO 8601) | Target date for completion |

### ControlReference Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `controlId` | string | Identifier of the control |
| `controlType` | string | Type of control (`policy`, `procedure`, `technical`, `physical`) |
| `effectiveness` | string | Assessed effectiveness of the control (`low`, `medium`, `high`) |
| `lastTested` | string (ISO 8601) | Timestamp when the control was last tested |
| `testResult` | string | Result of the last test (`passed`, `failed`, `partial`) |

### Required Fields
- `riskId`
- `name`
- `version`
- `riskType`
- `category`
- `likelihood`
- `impact`
- `riskScore`
- `riskOwner`
- `riskOwnerType`
- `effectiveFrom`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `mitigationStrategies`
- `existingControls`
- `effectiveUntil`
- `tags`
- `metadata`

### Validation Rules
#### Governance-Specific Validation
- `riskType` must be one of: `operational`, `security`, `compliance`, `strategic`, `financial`, `reputational`
- `likelihood` must be one of: `rare`, `unlikely`, `possible`, `likely`, `almost_certain`
- `impact` must be one of: `insignificant`, `minor`, `moderate`, `major`, `catastrophic`
- `riskScore` must be a number between 1 and 25
- `riskOwnerType` must be one of: `agent`, `authority`, `governance_body`, `role`, `team`
- `type` in mitigation strategies must be one of: `preventive`, `detective`, `corrective`, `compensating`
- `effectiveness` in mitigation strategies must be one of: `low`, `medium`, `high`
- `implementationStatus` in mitigation strategies must be one of: `planned`, `in_progress`, `implemented`, `failed`
- `effectiveness` in control references must be one of: `low`, `medium`, `high`
- `testResult` in control references must be one of: `passed`, `failed`, `partial`
- If `effectiveUntil` is provided, it must be greater than `effectiveFrom`

#### Infrastructure Validation (see Part 12)
- `riskId` must conform to the UUID v4 standard
- `version` must follow semantic versioning
- `effectiveFrom` must conform to the ISO 8601 timestamp format
- If `effectiveUntil` is provided, it must conform to the ISO 8601 timestamp format and be greater than `effectiveFrom`
- `createdBy` must conform to the agent/user identifier format
- `createdAt` and `updatedAt` must conform to the ISO 8601 timestamp format
- `updatedAt` must be greater than or equal to `createdAt`

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Risk",
  "type": "object",
  "required": ["riskId", "name", "version", "riskType", "category", "likelihood", "impact", "riskScore", "riskOwner", "riskOwnerType", "effectiveFrom", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "riskId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "riskType": {
      "type": "string",
      "enum": ["operational", "security", "compliance", "strategic", "financial", "reputational"]
    },
    "category": { "type": "string", "minLength": 1 },
    "likelihood": {
      "type": "string",
      "enum": ["rare", "unlikely", "possible", "likely", "almost_certain"]
    },
    "impact": {
      "type": "string",
      "enum": ["insignificant", "minor", "moderate", "major", "catastrophic"]
    },
    "riskScore": {
      "type": "number",
      "minimum": 1,
      "maximum": 25
    },
    "riskOwner": { "type": "string", "minLength": 1 },
    "riskOwnerType": {
      "type": "string",
      "enum": ["agent", "authority", "governance_body", "role", "team"]
    },
    "mitigationStrategies": {
      "type": "array",
      "items": { "$ref": "#/definitions/mitigationStrategy" }
    },
    "existingControls": {
      "type": "array",
      "items": { "$ref": "#/definitions/controlReference" }
    },
    "effectiveFrom": { "type": "string", "format": "date-time" },
    "effectiveUntil": {
      "type": ["string", "null"],
      "format": "date-time"
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
    "mitigationStrategy": {
      "type": "object",
      "required": ["strategyId", "description", "type", "effectiveness", "implementationStatus"],
      "properties": {
        "strategyId": { "type": "string", "minLength": 1 },
        "description": { "type": "string" },
        "type": {
          "type": "string",
          "enum": ["preventive", "detective", "corrective", "compensating"]
        },
        "effectiveness": {
          "type": "string",
          "enum": ["low", "medium", "high"]
        },
        "implementationStatus": {
          "type": "string",
          "enum": ["planned", "in_progress", "implemented", "failed"]
        },
        "resourcesRequired": {
          "type": "object",
          "additionalProperties": true
        },
        "targetCompletionDate": { "type": "string", "format": "date-time" }
      }
    },
    "controlReference": {
      "type": "object",
      "required": ["controlId", "controlType", "effectiveness", "lastTested", "testResult"],
      "properties": {
        "controlId": { "type": "string", "minLength": 1 },
        "controlType": {
          "type": "string",
          "enum": ["policy", "procedure", "technical", "physical"]
        },
        "effectiveness": {
          "type": "string",
          "enum": ["low", "medium", "high"]
        },
        "lastTested": { "type": "string", "format": "date-time" },
        "testResult": {
          "type": "string",
          "enum": ["passed", "failed", "partial"]
        }
      }
    }
  }
}
```

### YAML Example
```yaml
riskId: "444e4567-e89b-12d3-a456-426614174100"
name: "Unauthorized PII Access Risk"
version: "1.0.0"
description: "Risk of unauthorized access to personally identifiable information through agent workflows"
riskType: "security"
category: "unauthorized_access"
likelihood: "possible"
impact: "major"
riskScore: 12
riskOwner: "privacy-officer-002"
riskOwnerType: "role"
mitigationStrategies:
  - strategyId: "mit-001"
    description: "Implement strict PII access controls with approval workflows"
    type: "preventive"
    effectiveness: "high"
    implementationStatus: "in_progress"
    resourcesRequired:
      personnel: 2
      budget: 50000
      tools: ["access-control-system", "audit-logging"]
    targetCompletionDate: "2026-12-31T00:00:00Z"
  - strategyId: "mit-002"
    description: "Monthly audit of PII access logs"
    type: "detective"
    effectiveness: "medium"
    implementationStatus: "planned"
    resourcesRequired:
      personnel: 1
      budget: 5000
      tools: ["audit-analysis-software"]
    targetCompletionDate: "2026-11-30T00:00:00Z"
existingControls:
  - controlId: "ctrl-policy-001"
    controlType: "policy"
    effectiveness: "high"
    lastTested: "2026-07-01T00:00:00Z"
    testResult: "passed"
  - controlId: "ctrl-tech-002"
    controlType: "technical"
    effectiveness: "medium"
    lastTested: "2026-07-15T00:00:00Z"
    testResult: "passed"
effectiveFrom: "2026-08-01T00:00:00Z"
createdBy: "governance-system"
createdAt: "2026-08-01T00:00:00Z"
updatedAt: "2026-08-01T00:00:00Z"
tags:
  - "pii"
  - "security"
  - "access-control"
metadata:
  dataClassification: "PII"
  reviewFrequency: "quarterly"
```

### Migration Rules
- When adding new risk types: Extend the `riskType` enum
- When adding new likelihood/impact levels: Extend the respective enums
- When adding new mitigation strategy types: Extend the mitigation strategy type enum
- When adding new control types: Extend the control type enum
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by risk management systems and governance, risk, and compliance (GRC) platforms
- References Policy Schema for control references that are policies
- References Authority Schema for risk ownership
- Related to Exception Schema for risk-based exceptions
- Used by audit systems for risk-based audit planning
- Used by decision systems for risk-informed decision making

---

## Compliance Schema

### Purpose
Defines the structure for recording compliance assessments, violations, and remediation activities against governance policies, standards, or regulations.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `complianceId` | string | Unique identifier for the compliance record (see Part 12 for UUID v4 definition) |
| `name` | string | Human-readable name for the compliance record |
| `version` | string | Semantic version of the compliance record (see Part 12 for semantic versioning rules) |
| `description` | string | Detailed description of the compliance assessment |
| `complianceType` | string | Type of compliance (`policy`, `regulation`, `standard`, `contract`) |
| `framework` | string | Name of the compliance framework or standard being assessed (e.g., `GDPR`, `HIPAA`, `SOX`, `ISO27001`) |
| `assessmentScope` | string | Scope of the assessment (`global`, `system`, `workflow`, `agent_group`, `agent`) |
| `targetEntityId` | string | Identifier of the entity being assessed (agentId, workflowId, systemId, etc.) |
| `targetEntityType` | string | Type of the entity being assessed (`agent`, `workflow`, `system`, `data`, `knowledge`) |
| `assessmentDate` | string (ISO 8601) | Date when the compliance assessment was performed |
| `assessmentResult` | string | Result of the assessment (`compliant`, `non_compliant`, `partially_compliant`, `not_applicable`) |
| `requirementsAssessed` | array[ComplianceRequirement] | List of specific requirements that were assessed |
| `violations` | array[ComplianceViolation] | List of specific violations found (if assessmentResult is non-compliant or partially_compliant) |
| `remediationPlan` | object | Plan for addressing violations (if any) |
| `effectiveFrom` | string (ISO 8601) | Timestamp when the compliance assessment becomes effective |
| `effectiveUntil` | string (ISO 8601) or null | Timestamp when the compliance assessment expires |
| `createdBy` | string | AgentId or userId that performed the compliance assessment |
| `createdAt` | string (ISO 8601) | Timestamp when the compliance record was created |
| `updatedAt` | string (ISO 8601) | Timestamp when the compliance record was last updated |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for compliance-specific metadata |

### ComplianceRequirement Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `requirementId` | string | Unique identifier for the requirement |
| `description` | string | Detailed description of the requirement |
| `requirementType` | string | Type of requirement (`data`, `data_protection`, `audit_logging`, `change_management`, etc.) |
| `status` | string | Compliance status for this requirement (`compliant`, `non_compliant`, `not_applicable`) |
| `evidence` | array[string] | List of evidence identifiers supporting the status assessment |
| `gapDescription` | string | Description of the gap if status is non_compliant |
| `remediationPriority` | string | Priority for remediation (`low`, `medium`, `high`, `critical`) |

### ComplianceViolation Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `violationId` | string | Unique identifier for the violation |
| `requirementId` | string | Identifier of the requirement that was violated |
| `description` | string | Detailed description of the violation |
| `severity` | string | Severity of the violation (`low`, `medium`, `high`, `critical`) |
| `detectedAt` | string (ISO 8601) | Timestamp when the violation was detected |
| `evidence` | array[string] | List of evidence identifiers supporting the violation |
| `remediationStatus` | string | Current status of remediation (`open`, `in_progress`, `resolved`, `accepted_risk`) |
| `remediationDueDate` | string (ISO 8601) | Date by which remediation should be completed |

### Required Fields
- `complianceId`
- `name`
- `version`
- `complianceType`
- `framework`
- `assessmentScope`
- `targetEntityId`
- `targetEntityType`
- `assessmentDate`
- `assessmentResult`
- `effectiveFrom`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `requirementsAssessed`
- `violations`
- `remediationPlan`
- `effectiveUntil`
- `tags`
- `metadata`

### Validation Rules
#### Governance-Specific Validation
- `complianceType` must be one of: `policy`, `regulation`, `standard`, `contract`
- `assessmentScope` must be one of: `global`, `system`, `workflow`, `agent_group`, `agent`
- `targetEntityType` must be one of: `agent`, `workflow`, `system`, `data`, `knowledge`
- `assessmentResult` must be one of: `compliant`, `non_compliant`, `partially_compliant`, `not_applicable`
- `status` in compliance requirements must be one of: `compliant`, `non_compliant`, `not_applicable`
- `severity` in compliance violations must be one of: `low`, `medium`, `high`, `critical`
- `remediationPriority` in compliance requirements must be one of: `low`, `medium`, `high`, `critical`
- `remediationStatus` in compliance violations must be one of: `open`, `in_progress`, `resolved`, `accepted_risk`
- If `effectiveUntil` is provided, it must be greater than `effectiveFrom`

#### Infrastructure Validation (see Part 12)
- `complianceId` must conform to the UUID v4 standard
- `version` must follow semantic versioning
- `assessmentDate` must conform to the ISO 8601 timestamp format
- `effectiveFrom` must conform to the ISO 8601 timestamp format
- If `effectiveUntil` is provided, it must conform to the ISO 8601 timestamp format and be greater than `effectiveFrom`
- `createdBy` must conform to the agent/user identifier format
- `createdAt` and `updatedAt` must conform to the ISO 8601 timestamp format
- `updatedAt` must be greater than or equal to `createdAt`

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Compliance",
  "type": "object",
  "required": ["complianceId", "name", "version", "complianceType", "framework", "assessmentScope", "targetEntityId", "targetEntityType", "assessmentDate", "assessmentResult", "effectiveFrom", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "complianceId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "complianceType": {
      "type": "string",
      "enum": ["policy", "regulation", "standard", "contract"]
    },
    "framework": { "type": "string", "minLength": 1 },
    "assessmentScope": {
      "type": "string",
      "enum": ["global", "system", "workflow", "agent_group", "agent"]
    },
    "targetEntityId": { "type": "string", "minLength": 1 },
    "targetEntityType": {
      "type": "string",
      "enum": ["agent", "workflow", "system", "data", "knowledge"]
    },
    "assessmentDate": { "type": "string", "format": "date-time" },
    "assessmentResult": {
      "type": "string",
      "enum": ["compliant", "non_compliant", "partially_compliant", "not_applicable"]
    },
    "requirementsAssessed": {
      "type": "array",
      "items": { "$ref": "#/definitions/complianceRequirement" }
    },
    "violations": {
      "type": "array",
      "items": { "$ref": "#/definitions/complianceViolation" }
    },
    "remediationPlan": {
      "type": "object",
      "additionalProperties": true
    },
    "effectiveFrom": { "type": "string", "format": "date-time" },
    "effectiveUntil": {
      "type": ["string", "null"],
      "format": "date-time"
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
    "complianceRequirement": {
      "type": "object",
      "required": ["requirementId", "description", "requirementType", "status"],
      "properties": {
        "requirementId": { "type": "string", "minLength": 1 },
        "description": { "type": "string" },
        "requirementType": { "type": "string", "minLength": 1 },
        "status": {
          "type": "string",
          "enum": ["compliant", "non_compliant", "not_applicable"]
        },
        "evidence": {
          "type": "array",
          "items": { "type": "string" }
        },
        "gapDescription": { "type": "string" },
        "remediationPriority": {
          "type": "string",
          "enum": ["low", "medium", "high", "critical"]
        }
      }
    },
    "complianceViolation": {
      "type": "object",
      "required": ["violationId", "requirementId", "description", "severity", "detectedAt", "evidence", "remediationStatus"],
      "properties": {
        "violationId": { "type": "string", "minLength": 1 },
        "requirementId": { "type": "string", "minLength": 1 },
        "description": { "type": "string" },
        "severity": {
          "type": "string",
          "enum": ["low", "medium", "high", "critical"]
        },
        "detectedAt": { "type": "string", "format": "date-time" },
        "evidence": {
          "type": "array",
          "items": { "type": "string" }
        },
        "remediationStatus": {
          "type": "string",
          "enum": ["open", "in_progress", "resolved", "accepted_risk"]
        },
        "remediationDueDate": { "type": "string", "format": "date-time" }
      }
    }
  }
}
```

### YAML Example
```yaml
complianceId: "888e4567-e89b-12d3-a456-426614174110"
name: "GDPR Compliance Assessment for Customer Data Workflow"
version: "1.0.0"
description: "Assessment of customer data workflow against GDPR requirements"
complianceType: "regulation"
framework: "GDPR"
assessmentScope: "workflow"
targetEntityId: "workflow-customer-data-001"
targetEntityType: "workflow"
assessmentDate: "2026-08-01T00:00:00Z"
assessmentResult: "partially_compliant"
requirementsAssessed:
  - requirementId: "req-gdpr-001"
    description: "Lawful basis for processing personal data"
    requirementType: "legal_basis"
    status: "compliant"
    evidence: ["consent-form-v2.1", "processing-record-2026-08"]
    gapDescription: null
    remediationPriority: "low"
  - requirementId: "req-gdpr-002"
    description: "Data subject right to access"
    requirementType: "data_subject_rights"
    status: "non_compliant"
    evidence: []
    gapDescription: "No automated process for data subject access requests"
    remediationPriority: "high"
violations:
  - violationId: "viol-gdpr-002"
    requirementId: "req-gdpr-002"
    description: "Lack of automated process for data subject access requests"
    severity: "high"
    detectedAt: "2026-08-01T00:00:00Z"
    evidence: ["process-review-2026-08", "interview-notes-2026-08"]
    remediationStatus: "in_progress"
    remediationDueDate: "2026-11-01T00:00:00Z"
remediationPlan:
  owner: "privacy-officer-002"
  targetCompletionDate: "2026-11-01T00:00:00Z"
  estimatedEffort: "2 weeks"
  steps:
    - "Design automated DSAR workflow"
    - "Implement verification process"
    - "Create audit trail for requests"
    - "Test with pilot group"
    - "Deploy to production"
effectiveFrom: "2026-08-01T00:00:00Z"
effectiveUntil: "2027-08-01T00:00:00Z"
createdBy: "compliance-officer-001"
createdAt: "2026-08-01T00:00:00Z"
updatedAt: "2026-08-01T00:00:00Z"
tags:
  - "gdpr"
  - "compliance"
  - "data-privacy"
metadata:
  assessorQualification: "CIPP/E"
  nextAssessmentDate: "2027-08-01T00:00:00Z"
```

### Migration Rules
- When adding new compliance types: Extend the `complianceType` enum
- When adding new assessment scopes: Extend the `assessmentScope` enum
- When adding new target entity types: Extend the `targetEntityType` enum
- When adding new assessment results: Extend the `assessmentResult` enum
- When adding new requirement types: No enum extension needed (free text field)
- When adding new severity levels: Extend the severity enum
- When adding new remediation priorities: Extend the remediation priority enum
- When adding new remediation statuses: Extend the remediation status enum
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by compliance management systems and GRC platforms
- References Policy Schema for policy-based compliance assessments
- References Risk Schema for compliance risk assessments
- Related to Exception Schema for compliance-based exceptions
- Used by audit systems for compliance evidence collection
- Used by decision systems for compliance-informed decision making

---

## Audit Schema

### Purpose
Defines the structure for recording audit activities, findings, evidence, and conclusions related to governance compliance and control effectiveness.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `auditId` | string | Unique identifier for the audit (see Part 12 for UUID v4 definition) |
| `name` | string | Human-readable name for the audit |
| `version` | string | Semantic version of the audit record (see Part 12 for semantic versioning rules) |
| `description` | string | Detailed description of the audit scope, objectives, and methodology |
| `auditType` | string | Type of audit (`compliance`, `security`, `operational`, `financial`, `ad_hoc`) |
| `auditScope` | string | Scope of the audit (`global`, `system`, `workflow`, `agent_group`, `agent`) |
| `targetEntityId` | string | Identifier of the entity being audited (agentId, workflowId, systemId, etc.) |
| `targetEntityType` | string | Type of the entity being audited (`agent`, `workflow`, `system`, `data`, `knowledge`) |
| `auditorId` | string | Identifier of the auditing entity or agent |
| `auditorType` | string | Type of the auditor (`internal_audit`, `external_audit`, `peer_review`, `automated_tool`) |
| `auditDate` | string (ISO 8601) | Date when the audit was conducted |
| `auditConclusion` | string | Overall conclusion of the audit (`pass`, `fail`, `qualified_pass`, `inconclusive`) |
| `findings` | array[AuditFinding] | List of specific audit findings |
| `evidence` | array[AuditEvidence] | List of evidence collected during the audit |
| `recommendations` | array[string] | List of recommendations for improvement |
| `effectiveFrom` | string (ISO 8601) | Timestamp when the audit record becomes effective |
| `effectiveUntil` | string (ISO 8601) or null | Timestamp when the audit record expires |
| `createdBy` | string | AgentId or userId that created the audit record |
| `createdAt` | string (ISO 8601) | Timestamp when the audit was recorded |
| `updatedAt` | string (ISO 8601) | Timestamp when the audit record was last updated |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for audit-specific metadata |

### AuditFinding Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `findingId` | string | Unique identifier for the finding |
| `description` | string | Detailed description of the finding |
| `category` | string | Category of the finding (`control_deficiency`, `policy_violation`, `procedure_non_compliance`, `opportunity_for_improvement`) |
| `severity` | string | Severity of the finding (`low`, `medium`, `high`, `critical`) |
| `status` | string | Status of the finding (`open`, `in_progress`, `resolved`, `accepted_risk`) |
| `rootCause` | string | Analysis of the root cause of the finding |
| `evidenceReferences` | array[string] | List of evidence identifiers supporting the finding |
| `correctiveAction` | string | Recommended corrective action |
| `targetCompletionDate` | string (ISO 8601) | Target date for corrective action completion |

### AuditEvidence Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `evidenceId` | string | Unique identifier for the evidence |
| `description` | string | Detailed description of the evidence |
| `evidenceType` | string | Type of evidence (`document`, `log`, `interview`, `observation`, `system_output`) |
| `collectedAt` | string (ISO 8601) | Timestamp when the evidence was collected |
| `collectedBy` | string | Identifier of who collected the evidence |
| `relevance` | string | Relevance to audit objectives (`high`, `medium`, `low`) |
| `authenticity` | string | Assessment of evidence authenticity (`verified`, `unverified`, `questionable`) |
| `confidentiality` | string | Classification of evidence confidentiality (`public`, `internal`, `confidential`, `restricted`) |

### Required Fields
- `auditId`
- `name`
- `version`
- `auditType`
- `auditScope`
- `targetEntityId`
- `targetEntityType`
- `auditorId`
- `auditorType`
- `auditDate`
- `auditConclusion`
- `effectiveFrom`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `findings`
- `evidence`
- `recommendations`
- `effectiveUntil`
- `tags`
- `metadata`

### Validation Rules
#### Governance-Specific Validation
- `auditType` must be one of: `compliance`, `security`, `operational`, `financial`, `ad_hoc`
- `auditScope` must be one of: `global`, `system`, `workflow`, `agent_group`, `agent`
- `targetEntityType` must be one of: `agent`, `workflow`, `system`, `data`, `knowledge`
- `auditorType` must be one of: `internal_audit`, `external_audit`, `peer_review`, `automated_tool`
- `auditConclusion` must be one of: `pass`, `fail`, `qualified_pass`, `inconclusive`
- `category` in audit findings must be one of: `control_deficiency`, `policy_violation`, `procedure_non_compliance`, `opportunity_for_improvement`
- `severity` in audit findings must be one of: `low`, `medium`, `high`, `critical`
- `status` in audit findings must be one of: `open`, `in_progress`, `resolved`, `accepted_risk`
- `evidenceType` in audit evidence must be one of: `document`, `log`, `interview`, `observation`, `system_output`
- `relevance` in audit evidence must be one of: `high`, `medium`, `low`
- `authenticity` in audit evidence must be one of: `verified`, `unverified`, `questionable`
- `confidentiality` in audit evidence must be one of: `public`, `internal`, `confidential`, `restricted`
- If `effectiveUntil` is provided, it must be greater than `effectiveFrom`

#### Infrastructure Validation (see Part 12)
- `audId` must conform to the UUID v4 standard
- `version` must follow semantic versioning
- `auditDate` must conform to the ISO 8601 timestamp format
- `effectiveFrom` must conform to the ISO 8601 timestamp format
- If `effectiveUntil` is provided, it must conform to the ISO 8601 timestamp format and be greater than `effectiveFrom`
- `createdBy` must conform to the agent/user identifier format
- `createdAt` and `updatedAt` must conform to the ISO 8601 timestamp format
- `updatedAt` must be greater than or equal to `createdAt`

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Audit",
  "type": "object",
  "required": ["auditId", "name", "version", "auditType", "auditScope", "targetEntityId", "targetEntityType", "auditorId", "auditorType", "auditDate", "auditConclusion", "effectiveFrom", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "auditId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "auditType": {
      "type": "string",
      "enum": ["compliance", "security", "operational", "financial", "ad_hoc"]
    },
    "auditScope": {
      "type": "string",
      "enum": ["global", "system", "workflow", "agent_group", "agent"]
    },
    "targetEntityId": { "type": "string", "minLength": 1 },
    "targetEntityType": {
      "type": "string",
      "enum": ["agent", "workflow", "system", "data", "knowledge"]
    },
    "auditorId": { "type": "string", "minLength": 1 },
    "auditorType": {
      "type": "string",
      "enum": ["internal_audit", "external_audit", "peer_review", "automated_tool"]
    },
    "auditDate": { "type": "string", "format": "date-time" },
    "auditConclusion": {
      "type": "string",
      "enum": ["pass", "fail", "qualified_pass", "inconclusive"]
    },
    "findings": {
      "type": "array",
      "items": { "$ref": "#/definitions/auditFinding" }
    },
    "evidence": {
      "type": "array",
      "items": { "$ref": "#/definitions/auditEvidence" }
    },
    "recommendations": {
      "type": "array",
      "items": { "type": "string" }
    },
    "effectiveFrom": { "type": "string", "format": "date-time" },
    "effectiveUntil": {
      "type": ["string", "null"],
      "format": "date-time"
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
    "auditFinding": {
      "type": "object",
      "required": ["findingId", "description", "category", "severity", "status"],
      "properties": {
        "findingId": { "type": "string", "minLength": 1 },
        "description": { "type": "string" },
        "category": {
          "type": "string",
          "enum": ["control_deficiency", "policy_violation", "procedure_non_compliance", "opportunity_for_improvement"]
        },
        "severity": {
          "type": "string",
          "enum": ["low", "medium", "high", "critical"]
        },
        "status": {
          "type": "string",
          "enum": ["open", "in_progress", "resolved", "accepted_risk"]
        },
        "rootCause": { "type": "string" },
        "evidenceReferences": {
          "type": "array",
          "items": { "type": "string" }
        },
        "correctiveAction": { "type": "string" },
        "targetCompletionDate": { "type": "string", "format": "date-time" }
      }
    },
    "auditEvidence": {
      "type": "object",
      "required": ["evidenceId", "description", "evidenceType", "collectedAt", "collectedBy", "relevance", "authenticity", "confidentiality"],
      "properties": {
        "evidenceId": { "type": "string", "minLength": 1 },
        "description": { "type": "string" },
        "evidenceType": {
          "type": "string",
          "enum": ["document", "log", "interview", "observation", "system_output"]
        },
        "collectedAt": { "type": "string", "format": "date-time" },
        "collectedBy": { "type": "string", "minLength": 1 },
        "relevance": {
          "type": "string",
          "enum": ["high", "medium", "low"]
        },
        "authenticity": {
          "type": "string",
          "enum": ["verified", "unverified", "questionable"]
        },
        "confidentiality": {
          "type": "string",
          "enum": ["public", "internal", "confidential", "restricted"]
        }
      }
    }
  }
}
```

### YAML Example
```yaml
auditId: "999e4567-e89b-12d3-a456-426614174120"
name: "Quarterly Security Audit of Customer Data Workflow"
version: "1.0.0"
description: "Audit of customer data workflow against security policies and controls"
auditType: "security"
auditScope: "workflow"
targetEntityId: "workflow-customer-data-001"
targetEntityType: "workflow"
auditorId: "internal-audit-team-001"
auditorType: "internal_audit"
auditDate: "2026-08-01T00:00:00Z"
auditConclusion: "qualified_pass"
findings:
  - findingId: "find-001"
    description: "Inconsistent application of data classification labels"
    category: "policy_violation"
    severity: "medium"
    status: "open"
    rootCause: "Lack of automated data classification tools"
    evidenceReferences: ["evidence-001", "evidence-002"]
    correctiveAction: "Implement automated data classification and integrate with workflow"
    targetCompletionDate: "2026-10-31T00:00:00Z"
  - findingId: "find-002"
    description: "Access log retention period below policy requirement"
    category: "control_deficiency"
    severity: "high"
    status: "in_progress"
    rootCause: "Misconfigured log rotation settings"
    evidenceReferences: ["evidence-003"]
    correctiveAction: "Update log rotation configuration to retain logs for 7 years"
    targetCompletionDate: "2026-09-15T00:00:00Z"
evidence:
  - evidenceId: "evidence-001"
    description: "Sample of data objects with missing or incorrect classification labels"
    evidenceType: "document"
    collectedAt: "2026-08-01T10:00:00Z"
    collectedBy: "auditor-001"
    relevance: "high"
    authenticity: "verified"
    confidentiality: "confidential"
  - evidenceId: "evidence-002"
    description: "Interview with data steward regarding classification procedures"
    evidenceType: "interview"
    collectedAt: "2026-08-01T14:00:00Z"
    collectedBy: "auditor-002"
    relevance: "medium"
    authenticity: "verified"
    confidentiality: "internal"
  - evidenceId: "evidence-003"
    description: "Log rotation configuration file showing current settings"
    evidenceType: "document"
    collectedAt: "2026-08-01T09:00:00Z"
    collectedBy: "auditor-003"
    relevance: "high"
    authenticity: "verified"
    confidentiality: "internal"
recommendations:
  - "Implement automated data classification solution"
  - "Update log retention policies to match business requirements"
  - "Conduct quarterly training on data handling procedures"
effectiveFrom: "2026-08-01T00:00:00Z"
effectiveUntil: "2027-08-01T00:00:00Z"
createdBy: "governance-system"
createdAt: "2026-08-01T00:00:00Z"
updatedAt: "2026-08-01T00:00:00Z"
tags:
  - "audit"
  - "security"
  - "data-privacy"
metadata:
  auditorCertification: "CISA"
  nextAuditDate: "2026-11-01T00:00:00Z"
```

### Migration Rules
- When adding new audit types: Extend the `auditType` enum
- When adding new audit scopes: Extend the `auditScope` enum
- When adding new target entity types: Extend the `targetEntityType` enum
- When adding new auditor types: Extend the `auditorType` enum
- When adding new audit conclusions: Extend the `auditConclusion` enum
- When adding new finding categories: Extend the finding category enum
- When adding new finding severities: Extend the finding severity enum
- When adding new finding statuses: Extend the finding status enum
- When adding new evidence types: Extend the evidence type enum
- When adding new relevance levels: Extend the relevance enum
- When adding new authenticity assessments: Extend the authenticity enum
- When adding new confidentiality classifications: Extend the confidentiality enum
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by audit management systems and GRC platforms
- References Policy Schema for audit criteria based on policies
- References Risk Schema for risk-based audit planning
- References Compliance Schema for compliance-based audits
- Related to Exception Schema for audit-based exceptions
- Used by decision systems for audit-informed decision making
- Used by remediation systems for tracking audit finding resolution

---

## Exception Schema

### Purpose
Defines the structure for recording exceptions to governance policies, allowing for controlled deviations from standard rules under specific conditions and with proper authorization.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `exceptionId` | string | Unique identifier for the exception (see Part 12 for UUID v4 definition) |
| `name` | string | Human-readable name for the exception |
| `version` | string | Semantic version of the exception record (see Part 12 for semantic versioning rules) |
| `description` | string | Detailed description of the exception, its purpose, and scope |
| `exceptionType` | string | Type of exception (`temporary`, `permanent`, `conditional`, `emergency`) |
| `policyId` | string | Identifier of the policy for which this exception is granted |
| `policyVersion` | string | Version of the policy that this exception applies to |
| `ruleId` | string or null | Identifier of the specific rule within the policy that is excepted (if null, exception applies to entire policy) |
| `justification` | string | Detailed justification for granting the exception |
| `grantedBy` | string | Identifier of the authority or entity granting the exception |
| `grantedByType` | string | Type of the granting entity (`authority`, `governance_body`, `role`, `agent`) |
| `grantedAt` | string (ISO 8601) | Timestamp when the exception was granted |
| `effectiveFrom` | string (ISO 8601) | Timestamp when the exception becomes effective |
| `effectiveUntil` | string (ISO 8601) or null | Timestamp when the exception expires |
| `conditions` | array[string] | List of conditions that must be met for the exception to apply |
| `subjectId` | string | Identifier of the entity or action the exception applies to (agentId, workflowId, resourceId, etc.) |
| `subjectType` | string | Type of the subject (`agent`, `workflow`, `resource`, `data`, `knowledge`) |
| `reviewDate` | string (ISO 8601) or null | Date when the exception should be reviewed for continuation or termination |
| `createdBy` | string | AgentId or userId that created the exception record |
| `createdAt` | string (ISO 8601) | Timestamp when the exception was recorded |
| `updatedAt` | string (ISO 8601) | Timestamp when the exception was last updated |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for exception-specific metadata |

### Required Fields
- `exceptionId`
- `name`
- `version`
- `exceptionType`
- `policyId`
- `policyVersion`
- `justification`
- `grantedBy`
- `grantedByType`
- `grantedAt`
- `effectiveFrom`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `ruleId`
- `conditions`
- `subjectId`
- `subjectType`
- `reviewDate`
- `effectiveUntil`
- `tags`
- `metadata`

### Validation Rules
#### Governance-Specific Validation
- `exceptionType` must be one of: `temporary`, `permanent`, `conditional`, `emergency`
- `grantedByType` must be one of: `authority`, `governance_body`, `role`, `agent`
- `subjectType` must be one of: `agent`, `workflow`, `resource`, `data`, `knowledge`
- If `ruleId` is provided, it must reference a valid ruleId within the specified policy
- If `effectiveUntil` is provided, it must be greater than `effectiveFrom`
- If `reviewDate` is provided, it must be greater than or equal to `effectiveFrom`

#### Infrastructure Validation (see Part 12)
- `exceptionId` must conform to the UUID v4 standard
- `version` must follow semantic versioning
- `policyId` must conform to the UUID v4 standard
- `grantedBy` must conform to the agent/user identifier format (if it's an agent/user) or UUID v4 (if it's an authority/governance body)
- `grantedAt` must conform to the ISO 8601 timestamp format
- `effectiveFrom` must conform to the ISO 8601 timestamp format
- If `effectiveUntil` is provided, it must conform to the ISO 8601 timestamp format and be greater than `effectiveFrom`
- `createdBy` must conform to the agent/user identifier format
- `createdAt` and `updatedAt` must conform to the ISO 8601 timestamp format
- `updatedAt` must be greater than or equal to `createdAt`

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Exception",
  "type": "object",
  "required": ["exceptionId", "name", "version", "exceptionType", "policyId", "policyVersion", "justification", "grantedBy", "grantedByType", "grantedAt", "effectiveFrom", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "exceptionId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "exceptionType": {
      "type": "string",
      "enum": ["temporary", "permanent", "conditional", "emergency"]
    },
    "policyId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "policyVersion": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "ruleId": {
      "oneOf": [
        {
          "type": "string",
          "minLength": 1
        },
        {
          "type": "null"
        }
      ]
    },
    "justification": { "type": "string" },
    "grantedBy": { "type": "string", "minLength": 1 },
    "grantedByType": {
      "type": "string",
      "enum": ["authority", "governance_body", "role", "agent"]
    },
    "grantedAt": { "type": "string", "format": "date-time" },
    "effectiveFrom": { "type": "string", "format": "date-time" },
    "effectiveUntil": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "conditions": {
      "type": "array",
      "items": { "type": "string" }
    },
    "subjectId": { "type": "string", "minLength": 1 },
    "subjectType": {
      "type": "string",
      "enum": ["agent", "workflow", "resource", "data", "knowledge"]
    },
    "reviewDate": {
      "oneOf": [
        {
          "type": "string",
          "format": "date-time"
        },
        {
          "type": "null"
        }
      ]
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
exceptionId: "222e4567-e89b-12d3-a456-426614174060"
name: "Research PII Access Exception"
version: "1.0.0"
description: "Temporary exception allowing anonymized PII access for approved research workflows"
exceptionType: "temporary"
policyId: "123e4567-e89b-12d3-a456-426614174024"
policyVersion: "1.0.0"
ruleId: "rule-001"
justification: "Research workflows demonstrate adequate anonymization techniques and operate under strict oversight, warranting exception to standard PII access prohibition."
grantedBy: "governance-council"
grantedByType: "governance_body"
grantedAt: "2026-08-01T00:00:00Z"
effectiveFrom: "2026-08-01T00:00:00Z"
effectiveUntil: "2027-08-01T00:00:00Z"
conditions:
  - "dataMustBeAnonymized"
  - "oversightCommitteeApprovalRequired"
  - "auditLoggingEnabled"
subjectId: "workflow-research-alpha-001"
subjectType: "workflow"
reviewDate: "2027-07-01T00:00:00Z"
createdBy: "governance-system"
createdAt: "2026-08-01T00:00:00Z"
updatedAt: "2026-08-01T00:00:00Z"
tags:
  - "exception"
  - "pii"
  - "research"
metadata:
  requestingEntity: "research-team-alpha"
  approvalReference: "gov-council-resolution-2026-08"
```

### Migration Rules
- When adding new exception types: Extend the `exceptionType` enum
- When adding new grantedBy types: Extend the `grantedByType` enum
- When adding new subject types: Extend the `subjectType` enum
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by exception management systems and policy engines
- References Policy Schema for the policy being excepted
- References Authority Schema for the granting entity
- Related to Decision Schema for recording exception grants as governance decisions
- Used by audit systems for tracking exception exercise and compliance
- Used by risk systems for risk-based exception evaluation

---

## Override Schema

### Purpose
Defines the structure for recording overrides of governance policies or decisions, allowing for authoritative changes to established governance determinations with proper justification and authorization.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `overrideId` | string | Unique identifier for the override (see Part 12 for UUID v4 definition) |
| `name` | string | Human-readable name for the override |
| `version` | string | Semantic version of the override record (see Part 12 for semantic versioning rules) |
| `description` | string | Detailed description of the override, its purpose, and scope |
| `overrideType` | string | Type of override (`policy_override`, `decision_override`, `exception_override`, `authority_override`) |
| `targetId` | string | Identifier of the entity being overridden (policyId, decisionId, exceptionId, authorityId) |
| `targetType` | string | Type of the entity being overridden (`policy`, `decision`, `exception`, `authority`) |
| `overrideAction` | string | Action taken by the override (`supersede`, `modify`, `nullify`, `extend`) |
| `justification` | string | Detailed justification for the override |
| `overridingAuthorityId` | string | Identifier of the authority issuing the override |
| `overridingAuthorityType` | string | Type of the overriding authority (`authority`, `governance_body`, `role`, `agent`) |
| `overriddenAt` | string (ISO 8601) | Timestamp when the override was issued |
| `effectiveFrom` | string (ISO 8601) | Timestamp when the override becomes effective |
| `effectiveUntil` | string (ISO 8601) or null | Timestamp when the override expires |
| `conditions` | array[string] | List of conditions that must be met for the override to apply |
| `sideEffects` | array[string] | List of known side effects or impacts of the override |
| `createdBy` | string | AgentId or userId that created the override record |
| `createdAt` | string (ISO 8601) | Timestamp when the override was recorded |
| `updatedAt` | string (ISO 8601) | Timestamp when the override was last updated |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for override-specific metadata |

### Required Fields
- `overrideId`
- `name`
- `version`
- `overrideType`
- `targetId`
- `targetType`
- `overrideAction`
- `justification`
- `overridingAuthorityId`
- `overridingAuthorityType`
- `overriddenAt`
- `effectiveFrom`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `conditions`
- `sideEffects`
- `effectiveUntil`
- `tags`
- `metadata`

### Validation Rules
#### Governance-Specific Validation
- `overrideType` must be one of: `policy_override`, `decision_override`, `exception_override`, `authority_override`
- `targetType` must be one of: `policy`, `decision`, `exception`, `authority`
- `overrideAction` must be one of: `supersede`, `modify`, `nullify`, `extend`
- `overridingAuthorityType` must be one of: `authority`, `governance_body`, `role`, `agent`
- If `effectiveUntil` is provided, it must be greater than `effectiveFrom`
- If `conditions` is provided, each condition must be a non-empty string
- If `sideEffects` is provided, each side effect must be a non-empty string

#### Infrastructure Validation (see Part 12)
- `overrideId` must conform to the UUID v4 standard
- `version` must follow semantic versioning
- `targetId` must conform to the appropriate identifier format based on `targetType` (UUID v4 for policy/decision/exception/authority)
- `overridingAuthorityId` must conform to the agent/user identifier format (if it's an agent/user) or UUID v4 (if it's an authority/governance body)
- `overriddenAt` must conform to the ISO 8601 timestamp format
- `effectiveFrom` must conform to the ISO 8601 timestamp format
- If `effectiveUntil` is provided, it must conform to the ISO 8601 timestamp format and be greater than `effectiveFrom`
- `createdBy` must conform to the agent/user identifier format
- `createdAt` and `updatedAt` must conform to the ISO 8601 timestamp format
- `updatedAt` must be greater than or equal to `createdAt`

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Override",
  "type": "object",
  "required": ["overrideId", "name", "version", "overrideType", "targetId", "targetType", "overrideAction", "justification", "overridingAuthorityId", "overridingAuthorityType", "overriddenAt", "effectiveFrom", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "overrideId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "overrideType": {
      "type": "string",
      "enum": ["policy_override", "decision_override", "exception_override", "authority_override"]
    },
    "targetId": {
      "oneOf": [
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        }
      ]
    },
    "targetType": {
      "type": "string",
      "enum": ["policy", "decision", "exception", "authority"]
    },
    "overrideAction": {
      "type": "string",
      "enum": ["supersede", "modify", "nullify", "extend"]
    },
    "justification": { "type": "string" },
    "overridingAuthorityId": { "type": "string", "minLength": 1 },
    "overridingAuthorityType": {
      "type": "string",
      "enum": ["authority", "governance_body", "role", "agent"]
    },
    "overriddenAt": { "type": "string", "format": "date-time" },
    "effectiveFrom": { "type": "string", "format": "date-time" },
    "effectiveUntil": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "conditions": {
      "type": "array",
      "items": { "type": "string" }
    },
    "sideEffects": {
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
overrideId: "666e4567-e89b-12d3-a456-426614174080"
name: "Emergency PII Access Override"
version: "1.0.0"
description: "Overrides standard PII access prohibition for emergency medical response"
overrideType: "policy_override"
targetId: "123e4567-e89b-12d3-a456-426614174024"
targetType: "policy"
overrideAction: "modify"
justification: "Emergency medical situation requires immediate access to patient PII for life-saving treatment"
overridingAuthorityId: "emergency-response-authority-001"
overridingAuthorityType: "authority"
overriddenAt: "2026-08-01T00:00:00Z"
effectiveFrom: "2026-08-01T00:00:00Z"
effectiveUntil: "2026-08-02T00:00:00Z"
conditions:
  - "emergencySituationDeclared"
  - "limitedToMedicalPersonnel"
  - "auditLoggingRequired"
sideEffects:
  - "Temporary suspension of standard PII access controls"
  - "Increased audit review burden post-emergency"
createdBy: "governance-system"
createdAt: "2026-08-01T00:00:00Z"
updatedAt: "2026-08-01T00:00:00Z"
tags:
  - "override"
  - "emergency"
  - "pii"
metadata:
  emergencyDeclaration: "med-emerg-2026-08-001"
  medicalJustification: "Life-threatening patient condition requiring immediate intervention"
```

### Migration Rules
- When adding new override types: Extend the `overrideType` enum
- When adding new target types: Extend the `targetType` enum
- When adding new override actions: Extend the `overrideAction` enum
- When adding new authority types: Extend the `overridingAuthorityType` enum
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by override management systems and governance engines
- References Policy, Decision, Exception, and Authority schemas for target entities
- References Authority Schema for overriding authorities
- Related to Decision Schema for recording overrides as governance decisions
- Used by audit systems for tracking override exercise and compliance
- Used by policy systems for resolving policy conflicts

---

## RiskAssessment Schema

### Purpose
Defines the structure for documenting formal risk assessments, including risk identification, analysis, evaluation, and treatment recommendations.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `assessmentId` | string | Unique identifier for the risk assessment (see Part 12 for UUID v4 definition) |
| `name` | string | Human-readable name for the risk assessment |
| `version` | string | Semantic version of the risk assessment record (see Part 12 for semantic versioning rules) |
| `description` | string | Detailed description of the assessment scope, methodology, and objectives |
| `assessmentType` | string | Type of risk assessment (`initial`, `periodic`, `event_driven`, `change_driven`) |
| `assessmentScope` | string | Scope of the assessment (`global`, `system`, `workflow`, `agent_group`, `agent`) |
| `targetEntityId` | string | Identifier of the entity being assessed (agentId, workflowId, systemId, etc.) |
| `targetEntityType` | string | Type of the entity being assessed (`agent`, `workflow`, `system`, `data`, `knowledge`) |
| `assessmentDate` | string (ISO 8601) | Date when the risk assessment was performed |
| `riskIdentification` | array[RiskIdentification] | List of risks identified during the assessment |
| `riskAnalysis` | array[RiskAnalysis] | List of risk analyses performed (likelihood, impact, risk rating) |
| `riskEvaluation` | string | Overall risk evaluation (`low`, `medium`, `high`, `extreme`) |
| `riskTreatment` | array[RiskTreatment] | List of recommended risk treatments or mitigation actions |
| `responsibleParty` | string | Identifier of the party responsible for implementing risk treatments |
| `responsiblePartyType` | string | Type of the responsible party (`agent`, `authority`, `governance_body`, `role`, `team`) |
| `reviewDate` | string (ISO 8601) or null | Date when the risk assessment should be reviewed |
| `effectiveFrom` | string (ISO 8601) | Timestamp when the risk assessment becomes effective |
| `effectiveUntil` | string (ISO 8601) or null | Timestamp when the risk assessment expires |
| `createdBy` | string | AgentId or userId that performed the risk assessment |
| `createdAt` | string (ISO 8601) | Timestamp when the risk assessment record was created |
| `updatedAt` | string (ISO 8601) | Timestamp when the risk assessment record was last updated |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for risk assessment-specific metadata |

### RiskIdentification Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `riskId` | string | Unique identifier for the identified risk |
| `description` | string | Detailed description of the risk |
| `riskCategory` | string | Category of risk (`strategic`, `operational`, `financial`, `compliance`, `reputational`, `security`) |
| `riskSource` | string | Source or origin of the risk (`internal`, `external`, `threat`, `vulnerability`) |

### RiskAnalysis Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `riskId` | string | Reference to the risk being analyzed |
| `likelihood` | string | Assessed likelihood (`rare`, `unlikely`, `possible`, `likely`, `almost_certain`) |
| `impact` | string | Assessed impact (`insignificant`, `minor`, `moderate`, `major`, `catastrophic`) |
| `riskRating` | string | Calculated risk rating (`low`, `medium`, `high`, `extreme`) |
| `justification` | string | Explanation of the likelihood and impact assessment |
| `confidenceLevel` | string | Confidence in the assessment (`low`, `medium`, `high`) |

### RiskTreatment Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `treatmentId` | string | Unique identifier for the risk treatment |
| `riskId` | string | Reference to the risk being treated |
| `treatmentType` | string | Type of treatment (`avoid`, `transfer`, `mitigate`, `accept`) |
| `description` | string | Detailed description of the treatment |
| `priority` | string | Priority for implementation (`low`, `medium`, `high`, `critical`) |
| `responsibleParty` | string | Identifier of the party responsible for implementation |
| `targetCompletionDate` | string (ISO 8601) | Target date for completion |
| `resourcesRequired` | object | Resources needed (personnel, budget, tools) |
| `successCriteria` | array[string] | Criteria for determining treatment success |

### Required Fields
- `assessmentId`
- `name`
- `version`
- `assessmentType`
- `assessmentScope`
- `targetEntityId`
- `targetEntityType`
- `assessmentDate`
- `riskIdentification`
- `riskAnalysis`
- `riskEvaluation`
- `riskTreatment`
- `responsibleParty`
- `responsiblePartyType`
- `effectiveFrom`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `reviewDate`
- `effectiveUntil`
- `tags`
- `metadata`

### Validation Rules
#### Governance-Specific Validation
- `assessmentType` must be one of: `initial`, `periodic`, `event_driven`, `change_driven`
- `assessmentScope` must be one of: `global`, `system`, `workflow`, `agent_group`, `agent`
- `targetEntityType` must be one of: `agent`, `workflow`, `system`, `data`, `knowledge`
- `riskEvaluation` must be one of: `low`, `medium`, `high`, `extreme`
- `riskRating` in risk analysis must be one of: `low`, `medium`, `high`, `extreme`
- `likelihood` in risk analysis must be one of: `rare`, `unlikely`, `possible`, `likely`, `almost_certain`
- `impact` in risk analysis must be one of: `insignificant`, `minor`, `moderate`, `major`, `catastrophic`
- `treatmentType` in risk treatment must be one of: `avoid`, `transfer`, `mitigate`, `accept`
- `priority` in risk treatment must be one of: `low`, `medium`, `high`, `critical`
- `responsiblePartyType` must be one of: `agent`, `authority`, `governance_body`, `role`, `team`
- If `effectiveUntil` is provided, it must be greater than `effectiveFrom`
- If `reviewDate` is provided, it must be greater than or equal to `effectiveFrom`

#### Infrastructure Validation (see Part 12)
- `assessmentId` must conform to the UUID v4 standard
- `version` must follow semantic versioning
- `assessmentDate` must conform to the ISO 8601 timestamp format
- `effectiveFrom` must conform to the ISO 8601 timestamp format
- If `effectiveUntil` is provided, it must conform to the ISO 8601 timestamp format and be greater than `effectiveFrom`
- `createdBy` must conform to the agent/user identifier format
- `createdAt` and `updatedAt` must conform to the ISO 8601 timestamp format
- `updatedAt` must be greater than or equal to `createdAt`

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "RiskAssessment",
  "type": "object",
  "required": ["assessmentId", "name", "version", "assessmentType", "assessmentScope", "targetEntityId", "targetEntityType", "assessmentDate", "riskIdentification", "riskAnalysis", "riskEvaluation", "riskTreatment", "responsibleParty", "responsiblePartyType", "effectiveFrom", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "assessmentId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "assessmentType": {
      "type": "string",
      "enum": ["initial", "periodic", "event_driven", "change_driven"]
    },
    "assessmentScope": {
      "type": "string",
      "enum": ["global", "system", "workflow", "agent_group", "agent"]
    },
    "targetEntityId": { "type": "string", "minLength": 1 },
    "targetEntityType": {
      "type": "string",
      "enum": ["agent", "workflow", "system", "data", "knowledge"]
    },
    "assessmentDate": { "type": "string", "format": "date-time" },
    "riskIdentification": {
      "type": "array",
      "items": { "$ref": "#/definitions/riskIdentification" },
      "minItems": 1
    },
    "riskAnalysis": {
      "type": "array",
      "items": { "$ref": "#/definitions/riskAnalysis" }
    },
    "riskEvaluation": {
      "type": "string",
      "enum": ["low", "medium", "high", "extreme"]
    },
    "riskTreatment": {
      "type": "array",
      "items": { "$ref": "#/definitions/riskTreatment" }
    },
    "responsibleParty": { "type": "string", "minLength": 1 },
    "responsiblePartyType": {
      "type": "string",
      "enum": ["agent", "authority", "governance_body", "role", "team"]
    },
    "reviewDate": {
      "oneOf": [
        {
          "type": "string",
          "format": "date-time"
        },
        {
          "type": "null"
        }
      ]
    },
    "effectiveFrom": { "type": "string", "format": "date-time" },
    "effectiveUntil": {
      "type": ["string", "null"],
      "format": "date-time"
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
    "riskIdentification": {
      "type": "object",
      "required": ["riskId", "description", "riskCategory", "riskSource"],
      "properties": {
        "riskId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "description": { "type": "string" },
        "riskCategory": {
          "type": "string",
          "enum": ["strategic", "operational", "financial", "compliance", "reputational", "security"]
        },
        "riskSource": {
          "type": "string",
          "enum": ["internal", "external", "threat", "vulnerability"]
        }
      }
    },
    "riskAnalysis": {
      "type": "object",
      "required": ["riskId", "likelihood", "impact", "riskRating", "justification"],
      "properties": {
        "riskId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "likelihood": {
          "type": "string",
          "enum": ["rare", "unlikely", "possible", "likely", "almost_certain"]
        },
        "impact": {
          "type": "string",
          "enum": ["insignificant", "minor", "moderate", "major", "catastrophic"]
        },
        "riskRating": {
          "type": "string",
          "enum": ["low", "medium", "high", "extreme"]
        },
        "justification": { "type": "string" },
        "confidenceLevel": {
          "type": "string",
          "enum": ["low", "medium", "high"]
        }
      }
    },
    "riskTreatment": {
      "type": "object",
      "required": ["treatmentId", "riskId", "treatmentType", "description", "priority", "responsibleParty", "targetCompletionDate"],
      "properties": {
        "treatmentId": { "type": "string", "minLength": 1 },
        "riskId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "treatmentType": {
          "type": "string",
          "enum": ["avoid", "transfer", "mitigate", "accept"]
        },
        "description": { "type": "string" },
        "priority": {
          "type": "string",
          "enum": ["low", "medium", "high", "critical"]
        },
        "responsibleParty": { "type": "string", "minLength": 1 },
        "targetCompletionDate": { "type": "string", "format": "date-time" },
        "resourcesRequired": {
          "type": "object",
          "additionalProperties": true
        },
        "successCriteria": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    }
  }
}
```

### YAML Example
```yaml
assessmentId: "101e4567-e89b-12d3-a456-426614174130"
name: "Annual Financial Systems Risk Assessment"
version: "1.0.0"
description: "Comprehensive risk assessment of financial transaction processing systems"
assessmentType: "periodic"
assessmentScope: "system"
targetEntityId: "financial-system-001"
targetEntityType: "system"
assessmentDate: "2026-08-01T00:00:00Z"
riskIdentification:
  - riskId: "risk-fin-001"
    description: "Risk of fraudulent transactions due to weak authentication controls"
    riskCategory: "financial"
    riskSource: "vulnerability"
  - riskId: "risk-fin-002"
    description: "Risk of system downtime due to inadequate disaster recovery procedures"
    riskCategory: "operational"
    riskSource: "vulnerability"
riskAnalysis:
  - riskId: "risk-fin-001"
    likelihood: "possible"
    impact: "major"
    riskRating: "high"
    justification: "Authentication controls show gaps in multi-factor implementation"
    confidenceLevel: "high"
  - riskId: "risk-fin-002"
    likelihood: "unlikely"
    impact: "catastrophic"
    riskRating: "high"
    justification: "Disaster recovery plan exists but not tested in 18 months"
    confidenceLevel: "medium"
riskEvaluation: "high"
riskTreatment:
  - treatmentId: "treat-fin-001"
    riskId: "risk-fin-001"
    treatmentType: "mitigate"
    description: "Implement multi-factor authentication for all financial transactions"
    priority: "high"
    responsibleParty: "security-officer-001"
    targetCompletionDate: "2026-10-31T00:00:00Z"
    resourcesRequired:
      personnel: 2
      budget: 75000
      tools: ["mfa-solution", "identity-management"]
    successCriteria:
      - "100% of financial transactions require MFA"
      - "Zero authentication bypass incidents"
  - treatmentId: "treat-fin-002"
    riskId: "risk-fin-002"
    treatmentType: "mitigate"
    description: "Update and test disaster recovery procedures"
    priority: "high"
    responsibleParty: "operations-manager-001"
    targetCompletionDate: "2026-09-30T00:00:00Z"
    resourcesRequired:
      personnel: 3
      budget: 50000
      tools: ["dr-testing-tools", "backup-validation"]
    successCriteria:
      - "DR plan tested and validated"
      - "Recovery time objectives met"
responsibleParty: "chief-risk-officer-001"
responsiblePartyType: "role"
reviewDate: "2027-08-01T00:00:00Z"
effectiveFrom: "2026-08-01T00:00:00Z"
effectiveUntil: "2027-08-01T00:00:00Z"
createdBy: "governance-system"
createdAt: "2026-08-01T00:00:00Z"
updatedAt: "2026-08-01T00:00:00Z"
tags:
  - "risk-assessment"
  - "financial"
  - "annual"
metadata:
  methodology: "ISO 31000"
  assessorQualification: "CRISC"
```

### Migration Rules
- When adding new assessment types: Extend the `assessmentType` enum
- When adding new assessment scopes: Extend the `assessmentScope` enum
- When adding new target entity types: Extend the `targetEntityType` enum
- When adding new risk categories: Extend the risk category enum
- When adding new risk sources: Extend the risk source enum
- When adding new risk evaluation levels: Extend the risk evaluation enum
- When adding new risk rating levels: Extend the risk rating enum
- When adding new likelihood levels: Extend the likelihood enum
- When adding new impact levels: Extend the impact enum
- When adding new treatment types: Extend the treatment type enum
- When adding new priority levels: Extend the priority enum
- When adding new responsible party types: Extend the responsible party type enum
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by risk management systems and GRC platforms
- References Risk Schema for individual risk definitions
- References Authority Schema for responsible party assignments
- Related to Exception Schema for risk-based exceptions
- Used by audit systems for risk-based audit planning
- Used by decision systems for risk-informed decision making
- Used by compliance systems for compliance risk assessment

---

## GovernanceSubject Schema

### Purpose
Defines the structure for identifying and describing entities that are subject to governance within the AI-OS ecosystem, including agents, workflows, resources, data, and knowledge assets.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `subjectId` | string | Unique identifier for the governance subject (see Part 12 for UUID v4 definition) |
| `name` | string | Human-readable name for the subject |
| `version` | string | Semantic version of the subject record (see Part 12 for semantic versioning rules) |
| `description` | string | Detailed description of the subject, its purpose, and characteristics |
| `subjectType` | string | Type of the subject (`agent`, `workflow`, `resource`, `data`, `knowledge`) |
| `subType` | string | More specific classification within the subject type (e.g., for agent: `assistant`, `orchestrator`, `specialist`) |
| `ownerId` | string | Identifier of the entity that owns or is responsible for this subject |
| `ownerType` | string | Type of the owner (`agent`, `authority`, `governance_body`, `role`, `team`) |
| `classification` | string | Security or sensitivity classification (`public`, `internal`, `confidential`, `restricted`) |
| `capabilities` | array[string] | List of capabilities or functions the subject possesses |
| `limitations` | array[string] | List of limitations or constraints on the subject |
| `dependencies` | array[SubjectDependency] | List of other subjects this subject depends on |
| `governancePolicies` | array[PolicyReference] | List of policies that govern this subject |
| `effectiveFrom` | string (ISO 8601) | Timestamp when the subject record becomes effective |
| `effectiveUntil` | string (ISO 8601) or null | Timestamp when the subject record expires |
| `createdBy` | string | AgentId or userId that created the subject record |
| `createdAt` | string (ISO 8601) | Timestamp when the subject was created |
| `updatedAt` | string (ISO 8601) | Timestamp when the subject record was last updated |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for subject-specific metadata |

### SubjectDependency Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `subjectId` | string | Identifier of the dependent subject |
| `dependencyType` | string | Type of dependency (`data`, `control`, `functional`, `temporal`) |
| `dependencyStrength` | string | Strength of the dependency (`weak`, `moderate`, `strong`) |
| `description` | string | Description of the dependency relationship |

### PolicyReference Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `policyId` | string | Reference to a policy by its ID |
| `version` | string | Specific version of the policy that applies |
| `weight` | number | Optional weight for weighted policy application (default: 1.0) |

### Required Fields
- `subjectId`
- `name`
- `version`
- `subjectType`
- `ownerId`
- `ownerType`
- `classification`
- `effectiveFrom`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `subType`
- `capabilities`
- `limitations`
- `dependencies`
- `governancePolicies`
- `effectiveUntil`
- `tags`
- `metadata`

### Validation Rules
#### Governance-Specific Validation
- `subjectType` must be one of: `agent`, `workflow`, `resource`, `data`, `knowledge`
- `ownerType` must be one of: `agent`, `authority`, `governance_body`, `role`, `team`
- `classification` must be one of: `public`, `internal`, `confidential`, `restricted`, `personal`, `controlled`
- `dependencyType` in subject dependencies must be one of: `data`, `control`, `functional`, `temporal`
- `dependencyStrength` in subject dependencies must be one of: `weak`, `moderate`, `strong`
- If `effectiveUntil` is provided, it must be greater than `effectiveFrom`

#### Infrastructure Validation (see Part 12)
- `subjectId` must conform to the UUID v4 standard
- `version` must follow semantic versioning
- `effectiveFrom` must conform to the ISO 8601 timestamp format
- If `effectiveUntil` is provided, it must conform to the ISO 8601 timestamp format and be greater than `effectiveFrom`
- `createdBy` must conform to the agent/user identifier format
- `createdAt` and `updatedAt` must conform to the ISO 8601 timestamp format
- `updatedAt` must be greater than or equal to `createdAt`

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "GovernanceSubject",
  "type": "object",
  "required": ["subjectId", "name", "version", "subjectType", "ownerId", "ownerType", "classification", "effectiveFrom", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "subjectId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "subjectType": {
      "type": "string",
      "enum": ["agent", "workflow", "resource", "data", "knowledge"]
    },
    "subType": { "type": "string", "minLength": 1 },
    "ownerId": { "type": "string", "minLength": 1 },
    "ownerType": {
      "type": "string",
      "enum": ["agent", "authority", "governance_body", "role", "team"]
    },
    "classification": {
      "type": "string",
      "enum": ["public", "internal", "confidential", "restricted", "personal", "controlled"]
    },
    "capabilities": {
      "type": "array",
      "items": { "type": "string" }
    },
    "limitations": {
      "type": "array",
      "items": { "type": "string" }
    },
    "dependencies": {
      "type": "array",
      "items": { "$ref": "#/definitions/subjectDependency" }
    },
    "governancePolicies": {
      "type": "array",
      "items": { "$ref": "#/definitions/policyReference" }
    },
    "effectiveFrom": { "type": "string", "format": "date-time" },
    "effectiveUntil": {
      "type": ["string", "null"],
      "format": "date-time"
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
    "subjectDependency": {
      "type": "object",
      "required": ["subjectId", "dependencyType", "dependencyStrength"],
      "properties": {
        "subjectId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "dependencyType": {
          "type": "string",
          "enum": ["data", "control", "functional", "temporal"]
        },
        "dependencyStrength": {
          "type": "string",
          "enum": ["weak", "moderate", "strong"]
        },
        "description": { "type": "string" }
      }
    },
    "policyReference": {
      "type": "object",
      "required": ["policyId", "version"],
      "properties": {
        "policyId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "version": {
          "type": "string",
          "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
        },
        "weight": {
          "type": "number",
          "minimum": 0
        }
      }
    }
  }
}
```

### YAML Example
```yaml
subjectId: "agent-research-assistant-001"
name: "Research Assistant Agent Alpha"
version: "1.0.0"
description: "Specialized agent for conducting literature reviews and data analysis in research workflows"
subjectType: "agent"
subType: "specialist"
ownerId: "research-team-alpha"
ownerType: "team"
classification: "confidential"
capabilities:
  - "literature-review"
  - "data-analysis"
  - "hypothesis-generation"
  - "report-writing"
limitations:
  - "cannot access PII without approval"
  - "maximum concurrent workflows: 5"
  - "requires supervision for novel methodologies"
dependencies:
  - subjectId: "data-research-repo-001"
    dependencyType: "data"
    dependencyStrength: "strong"
    description: "Requires access to research repository for literature and datasets"
  - subjectId: "workflow-literature-review-001"
    dependencyType: "functional"
    dependencyStrength: "moderate"
    description: "Depends on literature review workflow for initial data gathering"
governancePolicies:
  - policyId: "123e4567-e89b-12d3-a456-426614174024"
    version: "1.0.0"
    weight: 1.0
  - policyId: "123e4567-e89b-12d3-a456-426614174025"
    version: "1.1.0"
    weight: 0.5
effectiveFrom: "2026-08-01T00:00:00Z"
createdBy: "governance-system"
createdAt: "2026-08-01T00:00:00Z"
updatedAt: "2026-08-01T00:00:00Z"
tags:
  - "agent"
  - "research"
  - "assistant"
metadata:
  modelVersion: "nemotron-3-super-120b"
  maxContextLength: 32768
```

### Migration Rules
- When adding new subject types: Extend the `subjectType` enum
- When adding new owner types: Extend the `ownerType` enum
- When adding new classifications: Extend the `classification` enum
- When adding new dependency types: Extend the `dependencyType` enum
- When adding new dependency strengths: Extend the `dependencyStrength` enum
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by agent management systems and service registries
- References Policy Schema for governance policies that apply to the subject
- References Authority Schema for ownership assignments
- Related to Decision Schema for recording decisions about the subject
- Used by audit systems for tracking subject activity and compliance
- Used by risk systems for risk assessment of subjects

---