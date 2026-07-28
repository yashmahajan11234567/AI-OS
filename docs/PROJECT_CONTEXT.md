# AI-OS Project Context

## Purpose

AI-OS is a long-term Python-based AI Operating System.

Its goal is to become an AI software engineer capable of planning,
researching, implementing, testing, documenting, and maintaining software
projects while remaining modular, production-ready, and extensible.

This repository is intended to grow over time rather than be rewritten.

---

# Current Phase

Phase 1 — Foundation

Current objective:

Build a clean, production-quality Python package and CLI before implementing AI features.

Feature development is intentionally postponed until the core architecture is stable.

---

# Technology Stack

Current

- Python 3.12
- Typer
- Rich
- Pydantic
- PyYAML
- src-layout
- uv / pip
- Ruff
- mypy
- pytest

Future

- SQLite
- Docker
- Kubernetes
- MCP
- Graphify
- Obsidian
- Local LLMs
- Multi-model routing
- RAG
- Vector databases

---

# Repository Layout

AI-OS/

config/
docs/
examples/
logs/
plugins/
scripts/
src/
templates/
tests/

Python package:

src/aios

---

# Long-Term Capabilities

The completed AI-OS should eventually support:

- Planning
- Research
- Execution
- Testing
- Deployment
- Memory
- Workflow Engine
- Skills
- Agents
- Subagents
- MCP Servers
- Claude Code Compatibility
- Graphify
- Obsidian
- Local LLMs
- Cloud Models
- Multi-model Routing

---

# Architecture Principles

Always preserve these principles.

1. Modular
2. Production quality
3. Extensible
4. Minimal coupling
5. Testable
6. Configuration-driven
7. Typed
8. Documentation-first

---

# Current Work

Current task:

Fix Python packaging.

Current blocker:

pip install -e .

succeeds

but

import aios

fails with

ModuleNotFoundError

The CLI currently fails for the same reason.

Focus only on debugging packaging.

---

# Rules

Do NOT redesign the repository.

Do NOT rewrite architecture unless explicitly requested.

Prefer incremental improvements.

Always preserve backward compatibility whenever practical.

Explain why changes are necessary.

When modifying code:

1. Explain the problem.
2. Explain the proposed fix.
3. List affected files.
4. Wait for approval before large refactors.
5. Implement only the approved changes.

---

# Development Workflow

For every implementation:

1. Analyze
2. Plan
3. Explain
4. Implement
5. Test
6. Summarize

---

# AI Behaviour

When assisting this repository:

- Read this document first.
- Treat it as the project source of truth.
- Avoid making assumptions.
- Do not introduce unnecessary dependencies.
- Prefer maintainability over cleverness.
- Follow existing architecture.

---

# Completed Milestones

- Initial repository created
- src-layout adopted
- Typer CLI created
- Package structure cleaned
- Imports migrated from src.* → aios.*
- CLI entrypoint changed to
  aios.cli.main:app

---

# Next Milestone

Successfully execute

import aios

and

aios --help

without packaging errors.

After that:

Phase 2 begins.

---

Last Updated:


Phase 1 - Foundation
✔ Project structure
✔ Packaging
✔ Editable install
✔ CLI
✔ src-layout