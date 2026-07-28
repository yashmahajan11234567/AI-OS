# AI-OS

**AI-OS** is a modular AI operating system providing research, planning, memory, workflow, and execution engines for building intelligent agents and applications.

## Features

- **Research Engine** — Deep web research, synthesis, and fact-checking
- **Planning Engine** — Task decomposition, scheduling, and resource allocation
- **Memory System** — Long-term, short-term, and episodic memory with retrieval
- **Workflow Engine** — DAG-based workflows with checkpoints and replay
- **Execution Engine** — Sandboxed code execution and tool orchestration
- **MCP Integration** — Model Context Protocol server/client support
- **Agent System** — Multi-agent coordination and delegation
- **Skills** — Extensible skill registry and marketplace
- **Testing** — Built-in testing framework for AI workflows
- **Deployment** — Container and cloud deployment targets

## Installation

```bash
# From source (editable install for development)
pip install -e .

# Or from PyPI (when published)
pip install ai-os
```

Requires Python 3.12+

## Usage

```bash
# Show version
aios version

# Help
aios --help
```

## Project Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Foundation (CLI, config, packaging) | 🟢 In Progress |
| 2 | Research Engine | ⏳ Planned |
| 3 | Planning Engine | ⏳ Planned |
| 4 | Execution Engine | ⏳ Planned |
| 5 | Testing Framework | ⏳ Planned |
| 6 | Deployment | ⏳ Planned |

See [docs/Roadmap/roadmap.md](docs/Roadmap/roadmap.md) for details.

## Architecture

See [docs/Architecture/system-overview.md](docs/Architecture/system-overview.md) for the system architecture.

## Configuration

Configuration files live in `config/`:
- `global.yaml` — Global settings
- `models.yaml` — LLM model configurations
- `mcps.yaml` — MCP server definitions
- `skills.yaml` — Skill registry
- `defaults.yaml` — Default values

Copy `.env.example` to `.env` and add your API keys.

## License

MIT License — see [LICENSE](LICENSE) for details.