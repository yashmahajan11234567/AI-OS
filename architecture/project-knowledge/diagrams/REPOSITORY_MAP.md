# Repository Map — AI-OS

## Purpose

This document is the canonical map of the `AI-OS` repository. It explains who owns each area, how the areas relate, and which areas depend on which others. It is technology-neutral by design: it names directories, documents, and responsibilities, not frameworks or versions.

---

## Top-Level Ownership

| Area | Owner / Role | Nature |
|------|--------------|--------|
| `architecture/` | Architecture team / specification authors | Frozen specification and evolving architectural artifacts |
| `config/` | Platform / configuration owners | Runtime configuration and integration definitions |
| `data/` | Runtime / operators | Generated state, memory, logs, checkpoints |
| `docs/` | Documentation / product | User-facing and contributor-facing documentation |
| `examples/` | Developers / contributors | Usage examples and reference scenarios |
| `logs/` | Runtime / operators | Operational log output |
| `plugins/` | Contributors / integrators | Optional extension point directory |
| `scripts/` | Developers / CI | Automation, bootstrap, maintenance scripts |
| `src/aios/` | Core engineering team | Reference runtime implementation |
| `tests/` | QA / core engineering | Automated verification |
| `workspace/` | Runtime / operators | Ephemeral working state for the runtime |

---

## Repository Structure

```mermaid
flowchart TD
    subgraph AI_OS ["AI-OS Repository (C:\Development\AI-OS)"]
        direction TB

        ARCH["architecture/
        Spec, parts, governance, diagrams"]
        PK["architecture/project-knowledge/
        Working knowledge, prompts, research, templates"]
        DOCS["docs/
        User and contributor documentation"]
        SRC["src/aios/
        Reference runtime"]
        CONFIG["config/
        Runtime configuration"]
        DATA["data/
        Runtime state and memory"]
        TESTS["tests/
        Automated verification"]
        EXAMPLES["examples/
        Usage examples"]
        SCRIPTS["scripts/
        Automation and maintenance"]
        WORKSPACE["workspace/
        Ephemeral runtime workspace"]
        PLUGINS["plugins/
        Optional extensions"]
        LOGS["logs/
        Operational logs"]
    end

    ARCH -->|"defines contracts for"| SRC
    SRC -->|"reads"| CONFIG
    SRC -->|"writes/reads"| DATA
    SRC -->|"produces"| LOGS
    SRC -->|"uses"| WORKSPACE
    SRC -->|"loads"| PLUGINS
    TESTS -->|"verifies"| SRC
    TESTS -->|"may read"| CONFIG
    TESTS -->|"may use"| WORKSPACE
    SCRIPTS -->|"operate on"| CONFIG
    SCRIPTS -->|"maintain"| SRC
    EXAMPLES -->|"demonstrate"| SRC
    EXAMPLES -->|"reference"| CONFIG
    DOCS -->|"describes"| ARCH
    DOCS -->|"describes"| SRC
    DOCS -->|"describes"| CONFIG
```

---

## Architecture Area

```mermaid
flowchart LR
    subgraph ARCHITECTURE ["architecture/"]
        direction TB

        PARTS["Part00–Part13/
        Specification parts"]
        COMMON["Common/
        Shared architectural artifacts"]
        DIAGRAMS_ARCH["Diagrams/
        Architecture-level diagrams"]
        TEMPLATES_ARCH["Templates/
        ADR, part, review templates"]
        PROJECT_KNOWLEDGE["project-knowledge/
        Active knowledge base"]
    end

    PARTS -->|"uses"| COMMON
    PARTS -->|"visualized in"| DIAGRAMS_ARCH
    TEMPLATES_ARCH -->|"standardizes"| PARTS
    PROJECT_KNOWLEDGE -->|"supports authoring of"| PARTS
    PROJECT_KNOWLEDGE -->|"feeds"| DIAGRAMS_ARCH
```

**Ownership:** Architecture authors and reviewers.  
**Lifecycle:** `Part00–Part13` are frozen specification; `project-knowledge/` is active working material.  
**Audience:** Architects, reviewers, auditors, contributors.  
**Technology neutrality:** Specification and diagrams are written in Markdown; visualization targets Mermaid and rendered documentation.

---

## Project Knowledge Area

```mermaid
flowchart TD
    subgraph PROJECT_KNOWLEDGE ["architecture/pro-knowledge/"]
        direction TB

        PK_ARCH["Architecture documents
        ENGINEERING_PRINCIPLES.md
        ARCHITECTURE_DECISIONS.md
        MEMORY_ARCHITECTURE.md
        MCP_ECOSYSTEM.md
        SKILLS_ECOSYSTEM.md
        AI_AGENCY.md
        VALIDATION_ARCHITECTURE.md"]
        PK_PROMPTS["prompts/
        ARCHITECTURE_PROMPTS.md
        CLAUDE_PROMPTS.md
        CHATGPT_PROMPTS.md
        REVIEW_PROMPTS.md"]
        PK_RESEARCH["research/
        FUTURE_FEATURES.md
        GITHUB_REPOSITORIES.md
        PAPERS.md"]
        PK_TEMPLATES["templates/
        ADR_TEMPLATE.md
        PART_TEMPLATE.md
        REVIEW_TEMPLATE.md"]
        PK_DIAGRAMS["diagrams/
        OVERALL_ARCHITECTURE.md
        AGENT_FLOW.md
        MCP_FLOW.md
        MEMORY_FLOW.md
        WORKFLOW_FLOW.md
        REPOSITORY_MAP.md"]
        PK_MEETING["meeting-notes/
        PROJECT_LOG.md"]
        PK_MASTER["AI_OS_MASTER_CONTEXT.md
        ROADMAP.md
        ROADMAP_V2.md
        FUTURE_RESEARCH.md
        GLOSSARY.md
        IMPLEMENTATION_GUIDE.md
        VERSION_HISTORY.md
        REPOSITORY_ECOSYSTEM.md
        COUNCILS.md
        ARCHITECTURE_EVOLUTION.md"]
    end

    PK_ARCH -->|"authoring guided by"| PK_TEMPLATES
    PK_PROMPTS -->|"drive authoring of"| PK_ARCH
    PK_PROMPTS -->|"drive authoring of"| PK_MASTER
    PK_RESEARCH -->|"informs"| PK_ARCH
    PK_RESEARCH -->|"informs"| PK_MASTER
    PK_DIAGRAMS -->|"visualizes"| PK_ARCH
    PK_MEETING -->|"records decisions affecting"| PK_ARCH
    PK_MEETING -->|"records decisions affecting"| PK_MASTER
    PK_MASTER -->|"orchestrates"| PK_ARCH
    PK_MASTER -->|"orchestrates"| PK_PROMPTS
    PK_MASTER -->|"orchestrates"| PK_RESEARCH
```

**Ownership:** Architecture team and working authors.  
**Lifecycle:** Active; evolves continuously until specification parts are finalized.  
**Technology neutrality:** Plain Markdown documents; no execution environment required.

---

## Runtime Area

```mermaid
flowchart TD
    subgraph RUNTIME ["src/aios/ — Reference Runtime"]
        direction TB

        CORE["core/
        Kernel, interfaces, base managers"]
        AGENTS["agents/
        Agent lifecycle and behavior"]
        AI_AGENCY["ai_agency/
        AI Agency service"]
        CLI["cli/
        Command interface"]
        CONFIG_SRC["config/
        Configuration loading and validation"]
        COUNCIL["council/
        Governance and adjudication"]
        DEPLOYMENT["deployment/
        Packaging, containers, release"]
        EVENTS["events/
        Event bus, pub/sub"]
        INTEGRATIONS["integrations/
        External system adapters"]
        MCP_SRC["mcp/
        Model Context Protocol integration"]
        MEMORY["memory/
        Memory backends and retrieval"]
        OBSERVERS["observers/
        Observability instrumentation"]
        PLANNER["planner/
        Planning engine"]
        RESEARCH["research/
        Research engine"]
        SERVICES["services/
        Facade and orchestration services"]
    end

    CORE -->|"used by"| AGENTS
    CORE -->|"used by"| AI_AGENCY
    CORE -->|"used by"| COUNCIL
    CORE -->|"used by"| SERVICES
    EVENTS -->|"connects"| AGENTS
    EVENTS -->|"connects"| AI_AGENCY
    EVENTS -->|"connects"| COUNCIL
    EVENTS -->|"connects"| SERVICES
    CONFIG_SRC -->|"configures"| CORE
    CONFIG_SRC -->|"configures"| CLI
    MEMORY -->|"used by"| AGENTS
    MEMORY -->|"used by"| AI_AGENCY
    MCP_SRC -->|"extends"| INTEGRATIONS
    OBSERVERS -->|"instrument"| CORE
    PLANNER -->|"uses"| SERVICES
    RESEARCH -->|"uses"| SERVICES
    DEPLOYMENT -->|"packages"| SRC_APP["src/aios/ application"]
    CLI -->|"exposes"| SERVICES
```

**Ownership:** Core engineering team.  
**Lifecycle:** Active development; implementation tracks the frozen architecture specification.  
**Technology neutrality:** Described by package/module responsibilities; actual implementation language and frameworks are not imposed by this map.

---

## Support and Verification Areas

```mermaid
flowchart TD
    subgraph SUPPORT ["Support and Verification"]
        direction TB

        CONFIG_DIR["config/
        YAML configuration"]
        DATA_DIR["data/
        Runtime state"]
        TESTS_DIR["tests/
        Verification suite"]
        EXAMPLES_DIR["examples/
        Reference usage"]
        SCRIPTS_DIR["scripts/
        Automation"]
        WORKSPACE_DIR["workspace/
        Ephemeral runtime state"]
        PLUGINS_DIR["plugins/
        Optional extensions"]
        LOGS_DIR["logs/
        Operational output"]
        DOCS_DIR["docs/
        Documentation"]
    end

    TESTS_DIR -->|"reads"| CONFIG_DIR
    TESTS_DIR -->|"uses"| WORKSPACE_DIR
    EXAMPLES_DIR -->|"demonstrate"| SRC["src/aios/"]
    EXAMPLES_DIR -->|"reference"| CONFIG_DIR
    SCRIPTS_DIR -->|"operate on"| CONFIG_DIR
    SCRIPTS_DIR -->|"maintain"| SRC
    DOCS_DIR -->|"describes"| ARCH_DIR["architecture/"]
    DOCS_DIR -->|"describes"| SRC
    DOCS_DIR -->|"describes"| CONFIG_DIR
```

**Ownership:**  
- `config/`: Platform owners and operators.  
- `data/`, `workspace/`, `logs/`: Runtime and operators.  
- `tests/`: QA and core engineering.  
- `examples/`: Contributors and developer advocates.  
- `scripts/`: Developers and CI maintainers.  
- `plugins/`: Contributors and integrators.  
- `docs/`: Documentation and product.  

**Lifecycle:**  
- `config/` and `tests/` are versioned with the runtime.  
- `data/`, `workspace/`, `logs/` are generated artifacts; excluded from source control.  
- `examples/`, `scripts/`, `plugins/` are versioned and evolve with the platform.  
- `docs/` is versioned and shipped with releases.

---

## Dependency Summary

```mermaid
flowchart LR
    ARCH["architecture/"]
    DOCS["docs/"]
    EXAMPLES["examples/"]
    SCRIPTS["scripts/"]
    SRC["src/aios/"]
    CONFIG["config/"]
    DATA["data/"]
    TESTS["tests/"]
    WORKSPACE["workspace/"]
    PLUGINS["plugins/"]
    LOGS["logs/"]

    ARCH -->|"governs"| SRC
    ARCH -->|"documented by"| DOCS
    SRC -->|"configured by"| CONFIG
    SRC -->|"state stored in"| DATA
    SRC -->|"verified by"| TESTS
    SRC -->|"demonstrated in"| EXAMPLES
    SRC -->|"operated by"| SCRIPTS
    SRC -->|"runtime workspace"| WORKSPACE
    SRC -->|"extends via"| PLUGINS
    SRC -->|"writes"| LOGS
    TESTS -->|"may read"| CONFIG
    TESTS -->|"may use"| WORKSPACE
    SCRIPTS -->|"modify"| CONFIG
    SCRIPTS -->|"maintain"| SRC
    DOCS -->|"describes"| ARCH
    DOCS -->|"describes"| SRC
    DOCS -->|"describes"| CONFIG
```

---

## Ownership and Governance Rules

1. **`architecture/`** is owned by the Architecture Review Board (ARB). Changes require formal review. `project-knowledge/` is working material and may be edited by contributors under normal review processes.
2. **`src/aios/`** is owned by the core engineering team. All changes require code review and passing tests.
3. **`config/`** is owned by the platform team. Changes require review of backward compatibility.
4. **`tests/`** is owned by QA and core engineering. Test coverage requirements are enforced for all changes to `src/aios/`.
5. **`docs/`** is owned by the documentation team. Accuracy is enforced by review and, where possible, by automated checks.
6. **`data/`, `workspace/`, `logs/`** are owned by operators and runtime. They are not source-controlled and may be regenerated or cleared.
7. **`examples/`, `scripts/`, `plugins/`** are community-contributable under the same contribution workflow as `src/aios/`.

---

## Publication Notes

- This map is versioned with the repository.
- Updates to ownership or dependency structure should be reflected here and cross-referenced in `architecture/project-knowledge/REPOSITORY_ECOSYSTEM.md`.
- Diagram rendering requires Mermaid support. Where Mermaid is unavailable, export to SVG/PNG via the repository’s diagram tooling.
