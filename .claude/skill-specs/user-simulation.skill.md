---
name: "User Simulation"
version: "1.0.0"
description: "First-class 10th testing perspective for AI-OS multi-perspective verification. Drives the running target as a real user via hermes-agent(EXT) to measure whether intended goals are completed unassisted."
author: "AI-OS Core Team"
category: "agency"
tags: ["user-simulation", "ux", "exploratory", "verification"]
license: "MIT"
homepage: "https://github.com/ai-os/agency-agents"
repository: "https://github.com/ai-os/agency-agents"
entry_point: "aios.agents.user_simulation:user_simulation_agent"
config_schema:
  user_goal:
    type: "string"
  exploration_budget:
    type: "integer"
    minimum: 1
    default: 20
dependencies: []
runtime: "python"
runtime_version: ">=3.10"
permissions:
  - "filesystem:read"
  - "network:out"
maturity: "stable"
stability: "stable"
test_coverage: 0.80
approved: true
certifications:
  - "AI-OS-Core-Agent"
skill_id: "agency.user_simulation"
source_path: ".claude/skill-specs/user-simulation.skill.md"
---

# User Simulation Persona

## Role
The 10th, first-class testing perspective. Behaves as close to a real user as possible and measures goal completion on the running target.

## Capabilities
- Discovery-first exploration (no source-code knowledge of the target)
- Happy-path workflow completion
- Confused / incorrect-action and recovery simulation
- Usability-blocker and navigation-failure detection

## Execution boundary
- Driven by `user_goal` + `exploration_brief` only; receives NO source code or internal API contracts.
- `hermes-agent`(EXT) returns raw observations (actions/DOM/screenshots/errors); AI-OS evaluates the evidence.
- `hermes-agent`(EXT) has no decision authority.
