# FINAL EXTERNAL INTEGRATION USER CHECKLIST

**AI-OS · User Configuration & Requirements Checklist**
**Date:** 2026-08-27
**Author:** Terminal 1 — Architecture/Planning Authority

## INSTRUCTIONS
This checklist consolidates everything needed from the user to enable real external integration.
Do NOT provide actual secrets, keys, or credentials in responses - only indicate PRESENT/ABSENT/UNKNOWN.

## CHECKLIST CATEGORIES
- **ALREADY KNOWN**: Determined from repository inspection
- **NEEDS USER CONFIRMATION**: Requires explicit user yes/no
- **NEEDS USER-PROVIDED PATH**: User must specify filesystem location
- **NEEDS USER-PROVIDED CREDENTIAL**: User must provide auth method (indicate method only)
- **NEEDS USER-PROVIDED ENDPOINT**: User must specify URL/endpoint
- **NEEDS SOFTWARE INSTALLATION**: User must install software locally
- **NEEDS EXTERNAL SERVICE RUNNING**: User must have service operational
- **OPTIONAL**: Not required for operation
- **NOT NEEDED**: Not applicable/not required

---

## 1. EXECUTION INTEGRATIONS

### 1.1 HERMES/ACP
| Requirement | Category | Details | User Action |
|-------------|----------|---------|-------------|
| hermes-agent repository | NEEDS SOFTWARE INSTALLATION | User must have hermes-agent cloned/installed | `git clone https://github.com/AI-OS-Initiative/hermes-agent` |
| hermes-agent ACP entry point | ALREADY KNOWN | `hermes-agent/acp_adapter/entry.py` exists | None |
| Working directory (cwd) | NEEDS USER-PROVIDED PATH | Path to hermes-agent root directory | Absolute path to hermes-agent repo |
| Python interpreter | ALREADY KNOWN | Available via `python`/`python3` in PATH | None |
| ACP session TTL | NEEDS USER CONFIRMATION | 0 = disabled, >0 = enabled seconds | Specify TTL or confirm 0 (disabled) |
| ACP allowlist configuration | ALREADY KNOWN | In `defaults.yaml` under capabilities | None |

### 1.2 HERMES/MCP (Fallback)
| Requirement | Category | Details | User Action |
|-------------|----------|---------|-------------|
| hermes-agent MCP server | NEEDS SOFTWARE INSTALLATION | User must run hermes-agent MCP server | `python -m hermes_agent.mcp_serve` |
| Working directory (cwd) | NEEDS USER-PROVIDED PATH | Path to hermes-agent root directory | Same as ACP cwd |
| MCP stdio transport | ALREADY KNOWN | Uses standard MCP stdio | None |
| MCP server availability | NEEDS EXTERNAL SERVICE RUNNING | Hermeas-agent MCP server must be running | Start MCP server process |

### 1.3 PLAYWRIGHT MCP
| Requirement | Category | Details | User Action |
|-------------|----------|---------|-------------|
| Node.js runtime | NEEDS SOFTWARE INSTALLATION | v18+ recommended | Install Node.js |
| @playwright/mcp package | NEEDS SOFTWARE INSTALLATION | npm package | `npm install -g @playwright/mcp` |
| Browser installation | NEEDS SOFTWARE INSTALLATION | Chromium/Firefox/WebKit | `npx playwright install` |
| Working directory | NEEDS USER-PROVIDED PATH | For MCP server cwd (optional) | Path or leave empty for default |
| Approved domains list | NEEDS USER PROVIDED LIST | Domains allowed for browser access | List of hostname patterns (e.g. ["*.example.com", "internal.*"]) |
| MCP server availability | NEEDS EXTERNAL SERVICE RUNNING | @playwright/mcp server must be running | `npx @playwright/mcp server` |
| Domain allowlist enforcement | ALREADY KNOWN | Built into adapter security context | None |

### 1.4 MCP GENERIC FRAMEWORK
| Requirement | Category | Details | User Action |
|-------------|----------|---------|-------------|
| MCP stdio server | DEPENDS ON INTEGRATION | Each integration brings its own MCP server | See specific integration |
| MCP transport | ALREADY KNOWN | stdio transport used | None |
| MCP manager | ALREADY KNOWN | MCPManager handles connections | None |

### 1.5 AGENT REACH
| Requirement | Category | Details | User Action |
|-------------|----------|---------|-------------|
| Agent Reach implementation | REFERENCE ONLY | See hermes-agent/skills/agent_reach/ | Consult documentation |
| Socket/HTTP endpoint | OPTIONAL | For external agent communication | Configure as needed |
| Registration as capability | OPTIONAL | Requires manifest creation | See capability manifest format |

### 1.6 SKILLSPECDTOR
| Requirement | Category | Details | User Action |
|-------------|----------|---------|-------------|
| Skill specifications | ALREADY KNOWN | In repository under skills/ | None |
| Skill execution | ALREADY KNOWN | Via SkillManager | None |
| External skill sources | OPTIONAL | Can import from external repos | Follow import procedures |
| Skill manifests | ALREADY KNOWN | YAML format in skills/ | None |

---

## 2. KNOWLEDGE INTEGRATIONS

### 2.1 OBSIDIAN
| Requirement | Category | Details | User Action |
|-------------|----------|---------|-------------|
| Obsidian application | NEEDS SOFTWARE INSTALLATION | Official Obsidian app | Download from obsidian.md |
| Vault location | NEEDS USER-PROVIDED PATH | Absolute path to vault directory | Path to existing or new vault |
| Vault permissions | NEEDS USER CONFIRMATION | Read/write access required | Confirm vault accessibility |
| MCP vs filesystem mode | NEEDS USER CONFIRMATION | Choose primary mode | Specify "mcp", "filesystem", or "hybrid" |
| Obsidian MCP server (if MCP mode) | NEEDS SOFTWARE INSTALLATION | Third-party MCP server | Install per Obsidian MCP docs |
| Frontmatter/wikilink handling | ALREADY KNOWN | Standard Obsidian format supported | None |
| Sync conflict resolution | ALREADY KNOWN | Last-write-wins with timestamps | None |

### 2.2 GRAPHIFY
| Requirement | Category | Details | User Action |
|-------------|----------|---------|-------------|
| Graphify backend/server | NEEDS EXTERNAL SERVICE RUNNING | Graphify service instance | Deploy/configure GraphifyBackend |
| Connection endpoint | NEEDS USER-PROVIDED ENDPOINT | URL or stdio command | HTTP endpoint or stdio command vector |
| Namespace isolation | NEEDS USER CONFIRMATION | Isolated namespace for AI-OS | Specify namespace prefix or pattern |
| Persistence requirements | NEEDS USER CONFIRMATION | Ephemeral vs persistent data | Specify data retention needs |
| Authentication method | NEEDS USER-PROVIDED CREDENTIAL | If required by backend | Specify method (token, basic, etc.) |
| Graph query language | ALREADY KNOWN | Supports standard graph queries | None |
| Update/delete operations | ALREADY KNOWN | Full CRUD supported | None |

### 2.3 CLAUDE-MEM
| Requirement | Category | Details | User Action |
|-------------|----------|---------|-------------|
| Claude-Mem implementation | REFERENCE ONLY | See architecture/references/ | Consult source material |
| MCP server availability | OPTIONAL | For external Claude-Mem instances | Run compatible MCP server |
| Local storage fallback | ALREADY KNOWN | Uses local MCPManager storage | None |
| Context retrieval methods | ALREADY KNOWN | retrieve_context, retrieve_by_tag, etc. | None |
| Advisory-only enforcement | ALREADY KNOWN | Hardened in adapter/security | None |

---

## 3. PLANNING INTEGRATIONS

### 3.1 NOTION
| Requirement | Category | Details | User Action |
|-------------|----------|---------|-------------|
| Notion account | NEEDS EXTERNAL SERVICE RUNNING | Active Notion account | Account must be accessible |
| Integration token | NEEDS USER-PROVIDED CREDENTIAL | Internal integration token | Create in Notion settings → Integrations |
| Database/page ID | NEEDS USER-PROVIDED ENDPOINT | Root object for operations | URL or ID of parent database/page |
| MCP server availability | NEEDS EXTERNAL SERVICE RUNNING | Notion MCP server compatibility | Use official or community MCP server |
| Approved operations | ALREADY KNOWN | search_pages, get_page, create_page, etc. | None |
| Rate limit handling | ALREADY KNOWN | Built-in retry with backoff | None |

### 3.2 GSD CORE
| Requirement | Category | Details | User Action |
|-------------|----------|---------|-------------|
| Methodology understanding | REFERENCE ONLY | GSD = Getting Things Done adaptation | Study referenced materials |
| Plugin/extension points | REFERENCE ONLY | See GSD Core documentation | None |
| Custom workflow integration | OPTIONAL | Adapt to existing workflows | As desired by user |
| Tool compatibility | REFERENCE ONLY | Works with standard task formats | None |

---

## 4. MODEL INFRASTRUCTURE

### 4.1 FREELLMAPI
| Requirement | Category | Details | User Action |
|-------------|----------|---------|-------------|
| FreeLLMAPI server | NEEDS EXTERNAL SERVICE RUNNING | Local LLM API server | Run compatible server |
| API endpoint | NEEDS USER-PROVIDED ENDPOINT | HTTP URL for API | e.g. `http://localhost:8080/v1` |
| API key (if required) | NEEDS USER-PROVIDED CREDENTIAL | Bearer token or key | As required by server implementation |
| Model availability | NEEDS USER CONFIRMATION | Specific models loaded | Confirm desired models available |
| Dev/test only enforcement | ALREADY KNOWN | C13 - no production without SLA | Accept dev/test limitation |
| Priority configuration | ALREADY KNOWN | Lower priority than commercial models | None |

### 4.2 STANDARD MODEL PROVIDERS
| Requirement | Category | Details | User Action |
|-------------|----------|---------|-------------|
| Anthropic API key | NEEDS USER-PROVIDED CREDENTIAL | Valid API key | Set `ANTHROPIC_API_KEY` env var |
| OpenAI API key | NEEDS USER-PROVIDED CREDENTIAL | Valid API key | Set `OPENAI_API_KEY` env var |
| Other providers | OPTIONAL | As supported by ModelRouter | Configure per provider docs |
| Model availability | NEEDS USER CONFIRMATION | Based on account/quota | Check provider limits |
| Fallback chains | ALREADY KNOWN | Configurable via ModelRouter | None |
| Cost tracking | ALREADY KNOWN | Usage statistics available | None |

---

## 5. COUNCIL/REVIEW STRATEGIES
All treated as techniques only - no external service dependencies.

---

## 6. REFERENCE/TECHNIQUE REPOSITORIES
All treated as technique sources only - user decides whether to:
- Import/adapt code (follow standard import procedures)
- Maintain as external reference
- Contribute back to upstream (separate from AI-OS)

---

## 7. SUMMARY BY CATEGORY

### EXECUTION
- **Hermes/ACP**: Needs hermes-agent installed + cwd path + ACP/MCP server running
- **Playwright MCP**: Needs Node.js + @playwright/mcp + browser + MCP server running  
- **MCP Framework**: Ready - depends on specific integration servers
- **Agent Reach**: Optional reference implementation
- **SkillSpecTor**: Ready - uses existing skill framework

### KNOWLEDGE  
- **Obsidian**: Needs Obsidian installed + vault path + read/write access
- **Graphify**: Needs GraphifyBackend running + connection details
- **Claude-Mem**: Optional - local storage or external MCP server

### PLANNING
- **Notion**: Needs Notion account + integration token + target database/page
- **GSD Core**: Reference methodology only

### MODEL INFRASTRUCTURE
- **FreeLLMAPI**: Needs local LLM server + endpoint + model availability (dev/test only)
- **Standard Providers**: Needs API keys for Anthropic/OpenAI/etc.

### IMPORTANT NOTES
1. **NEVER provide actual secrets/tokens/keys** - only indicate requirement exists
2. **All integrations are advisory-only** - AI-OS retains final authority
3. **Real operation requires explicit opt-in** - via `@pytest.mark.gated` + env vars
4. **Security gates enforce validation** - all connections route through SecurityManager
5. **Mock vs real clearly separated** - infrastructure preserved for both modes
6. **Local development works** - all integrations functional with mock servers

---
*User should indicate PRESENT/ABSENT/UNKNOWN for each requirement based on their environment and intentions.*