# M13 User Resource Checklist

## Overview

This document defines the definitive user resource checklist for AI-OS M13, specifying exactly what users must provide for real-mode operation of AI-OS M13 with all external integrations while preserving AI-OS as the sole governance, verification, and decision-making authority. The checklist specifies resources required for each integration (Supabase, n8n, Obsidian Git, AI-OS Dashboard, and existing external ecosystem) including environment variables, authentication requirements, network accessibility, software versions, and hardware requirements.

## Resource Categories

User resources are organized into these categories:
1. **Persistence Resources**: For data and state storage
2. **Execution Resources**: For workflow automation and bounded execution
3. **Knowledge Resources**: For knowledge/durability layers
4. **UI Resources**: For dashboard and interface access
5. **Communication Resources**: For agent communication and tool access
6. **Environment Variables**: Specific environment variables required
7. **Authentication Requirements**: Credentials and authentication mechanisms
8. **Network Requirements**: Network accessibility and firewall requirements
9. **Software Requirements**: Specific software and version requirements
10. **Hardware Requirements**: Hardware specifications and requirements
11. **Mock vs Real Mode**: Distinctions between mock and real mode operation
12. **Gated Real-Operational Tests**: Requirements for gated real operational testing
13. **Validation and Readiness**: How to validate resource readiness
14. **Deprecation and Alternates**: Resource deprecation policies and alternatives

## Persistence Resources

### Supabase
**Required for**: Persistent storage backend for AI-OS owned data
**User Must Provide**:
- Supabase project URL (e.g., https://your-project.supabase.co)
- Supabase anon/public key (for client-side operations)
- Optional: Supabase service role key (for admin operations, tightly controlled by AI-OS)
**Environment Variables**:
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_ANON_KEY`: Supabase anon/public key
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key (optional, for admin operations only)
**Authentication Requirements**:
- Anon/public key authentication for client-side operations
- Service role key authentication for admin operations (AI-OS controlled)
**Network Requirements**:
- HTTPS access to Supabase project URL
- Outbound network access to Supabase API endpoints
- Firewall rules allowing outbound HTTPS to Supabase domains
**Software Requirements**:
- Compatible web browser for Supabase dashboard access (optional)
- No client-side software required for AI-OS integration (uses standard HTTP/HTTPS)
**Hardware Requirements**:
- Network connectivity sufficient for Supabase API calls
- No specific hardware requirements beyond standard network capability
**Mock vs Real Mode**:
- **Mock Mode**: Automatic when Supabase credentials unavailable or invalid
- **Real Mode**: Requires valid Supabase URL and anon/public key
**Gated Real-Operational Tests**:
- Requires `AIOS_REAL_INTEGRATION_ENABLED=1` and verified Supabase credentials
- Tests actual Supabase connectivity, authentication, and persistence fidelity
**Validation and Readiness**:
- Validate Supabase URL is accessible via HTTPS
- Validate anon/public key format and validity
- Optional: Validate service role key format and validity (if provided)
- Integration framework tests Supabase connectivity before enabling real mode
**Deprecation and Alternates**:
- No planned deprecation for Supabase integration
- Alternative persistence systems could be added in future versions
- Local filesystem persistence always available as fallback

## Execution Resources

### n8n
**Required for**: Bounded automation/execution resource
**User Must Provide**:
- n8n instance URL (e.g., http://localhost:5678 or https://your-n8n-domain.com)
- n8n API key (generated in n8n Settings → API)
**Environment Variables**:
- `N8N_BASE_URL`: n8n instance URL
- `N8N_API_KEY`: n8n API key
**Authentication Requirements**:
- API key authentication via HTTP header (`X-N8N-API-KEY`)
- n8n instance must have API access enabled
**Network Requirements**:
- HTTP/HTTPS access to n8n instance URL
- Outbound network access to n8n API endpoints
- For remote n8n instances: firewall rules allowing access to n8n port (default 5678)
**Software Requirements**:
- Compatible web browser for n8n interface access (optional)
- n8n instance must be version 0.200.0 or later for full AI-OS compatibility
- No client-side software required for AI-OS integration (uses standard HTTP/HTTPS)
**Hardware Requirements**:
- Network connectivity sufficient for n8n API calls
- Host machine must meet n8n system requirements
- No specific hardware requirements beyond standard network capability
**Mock vs Real Mode**:
- **Mock Mode**: Automatic when n8n credentials unavailable or invalid
- **Real Mode**: Requires valid n8n instance URL and API key
**Gated Real-Operational Tests**:
- Requires `AIOS_REAL_INTEGRATION_ENABLED=1` and verified n8n credentials
- Tests actual n8n connectivity, authentication, workflow execution fidelity, and result validation
**Validation and Readiness**:
- Validate n8n instance URL is accessible via HTTP/HTTPS
- Validate n8n API key format and validity
- Integration framework tests n8n connectivity and authentication before enabling real mode
**Deprecation and Alternates**:
- No planned deprecation for n8n integration
- Alternative execution systems could be added in future versions
- Local agent execution always available as fallback (Hermes/ACP, Hermes/MCP, etc.)

## Knowledge Resources

### Obsidian + Obsidian Git
**Required for**: Knowledge/durability layer with actual durability guarantees
**User Must Provide**:
- Obsidian vault path (local directory containing Obsidian workspace)
- Git initialization in vault (`git init` performed in vault directory)
- Optional: Remote Git repository URL for durability distribution
**Environment Variables**:
- `OBSIDIAN_VAULT_PATH`: Absolute path to Obsidian vault directory
- `OBSIDIAN_GIT_REMOTE_URL`: Remote Git repository URL (optional, for durability distribution)
**Authentication Requirements**:
- File system access to Obsidian vault directory
- Git access to vault directory (for Git operations)
- Optional: Remote Git repository authentication (if remote URL provided)
**Network Requirements**:
- Local file system access to Obsidian vault directory
- Optional: Network access to remote Git repository (if remote URL provided)
- For remote Git: firewall rules allowing Git protocol access (SSH, HTTPS, etc.)
**Software Requirements**:
- Obsidian application installed and accessible
- Git installed and accessible in system PATH
- Optional: Git client for remote repository access (if remote URL provided)
- No client-side software required for AI-OS integration (uses direct file system/Git access)
**Hardware Requirements**:
- Local file system access sufficient for Obsidian vault operations
- Disk space sufficient for Obsidian vault and Git history
- Git executable accessible in system PATH
- No specific hardware requirements beyond standard file system capability
**Mock vs Real Mode**:
- **Mock Mode**: Automatic when Obsidian vault path unavailable or invalid
- **Real Mode**: Requires valid Obsidian vault path with Git initialization
**Gated Real-Operational Tests**:
- Requires `AIOS_REAL_INTEGRATION_ENABLED=1` and verified Obsidian/Git resources
- Tests actual Obsidian vault access, Git operations, knowledge persistence fidelity, and durability guarantees
**Validation and Readiness**:
- Validate Obsidian vault path exists and is accessible
- Validate Git is initialized in vault directory (`git rev-parse --is-inside-work-tree` returns true)
- Optional: Validate remote Git repository URL accessibility and authenticity
- Integration framework tests Obsidian vault access and Git initialization before enabling real mode
**Deprecation and Alternates**:
- No planned deprecation for Obsidian Git integration
- Alternative knowledge systems could be added in future versions
- Local file system knowledge persistence always available as fallback

## UI Resources

### AI-OS Dashboard
**Required for**: UI over AI-OS (read-only, user approval, AIOS authorized actions)
**User Must Provide**:
- Access to AI-OS Dashboard interface (localhost or network)
- Compatible browser or dashboard client for accessing the interface
- Optional: User credentials for dashboard authentication (if authentication implemented)
**Environment Variables**:
- `DASHBOARD_ENABLED`: Set to `1` to enable dashboard (optional, defaults to enabled)
- `DASHBOARD_HOST`: Dashboard host (optional, defaults to localhost)
- `DASHBOARD_PORT`: Dashboard port (optional, defaults to 3000)
- `DASHBOARD_AUTH_ENABLED`: Set to `1` to enable dashboard authentication (optional)
- `DASHBOARD_USERNAME`: Dashboard username (optional, if authentication enabled)
- `DASHBOARD_PASSWORD`: Dashboard password (optional, if authentication enabled)
**Authentication Requirements**:
- Optional: Username/password authentication for dashboard access
- Optional: Token-based authentication for dashboard access
- Optional: Integration with AI-OS authentication system
**Network Requirements**:
- Localhost access: AI-OS and dashboard must share execution environment
- Network access: Firewall rules allowing communication between AI-OS and dashboard
- For localhost: No additional network requirements beyond shared execution environment
- For network: Bi-directional network access between AI-OS execution environment and dashboard
**Software Requirements**:
- Compatible web browser (Chrome, Firefox, Safari, Edge, etc.)
- Optional: Dashboard client application (if provided)
- No client-side software required for AI-OS integration (uses standard HTTP/WebSocket)
**Hardware Requirements**:
- Device capable of running modern web browser
- Display sufficient for dashboard interface
- Input device (keyboard, mouse, touch, etc.) for dashboard interaction
- No specific hardware requirements beyond standard browser capability
**Mock vs Real Mode**:
- **Mock Mode**: Automatic when dashboard interface inaccessible or invalid
- **Real Mode**: Requires accessible dashboard interface and compatible browser/client
**Gated Real-Operational Tests**:
- Requires `AIOS_REAL_INTEGRATION_ENABLED=1` and verified dashboard accessibility
- Tests actual dashboard-UI-AI-OS communication, data display accuracy, and authorized action execution
**Validation and Readiness**:
- Validate dashboard interface is accessible (localhost or network)
- Validate compatible browser or client is available
- Validate network accessibility between AI-OS and dashboard (if network deployment)
- Integration framework tests dashboard accessibility before enabling real mode
**Deprecation and Alternates**:
- No planned deprecation for dashboard integration
- Alternative UI systems could be added in future versions
- Command-line interface (CLI) always available as fallback
- Direct API access always available as fallback

## Communication Resources

### Existing Ecosystem Components
All existing external integrations (Hermes/ACP, Hermes/MCP, Playwright, Agent Reach, FreeLLMAPI, Notion, Graphify, Claude-Mem) follow similar resource patterns:

#### Hermes/ACP
**Required for**: Direct agent-to-agent communication
**User Must Provide**: None (uses standard AI-OS inter-process communication)
**Environment Variables**: None
**Authentication Requirements**: None (AI-OS internal communication)
**Network Requirements**: None (uses standard AI-OS IPC mechanisms)
**Software Requirements**: None (built into AI-OS)
**Hardware Requirements**: None (uses standard AI-OS process capabilities)
**Mock vs Real Mode**: N/A (always real mode for internal AI-OS communication)
**Gated Real-Operational Tests**: N/A (internal AI-OS component)
**Validation and Readiness**: Always available as part of AI-OS core
**Deprecation and Alternates**: N/A (core AI-OS component)

#### Hermes/MCP
**Required for**: Standardized tool access for bounded capabilities
**User Must Provide**: None (uses standard AI-OS MCP framework)
**Environment Variables**: None
**Authentication Requirements**: None (AI-OS internal framework)
**Network Requirements**: None (uses standard AI-OS stdio subprocess communication)
**Software Requirements**: None (built into AI-OS)
**Hardware Requirements**: None (uses standard AI-OS process capabilities)
**Mock vs Real Mode**: N/A (always real mode for internal AI-OS framework)
**Gated Real-Operational Tests**: N/A (internal AI-OS component)
**Validation and Readiness**: Always available as part of AI-OS core
**Deprecation and Alternates**: N/A (core AI-OS framework)

#### Playwright
**Required for**: Browser-based testing and automation
**User Must Provide**:
- Playwright installation accessible to AI-OS
- Compatible browser binaries (Chromium, Firefox, WebKit) for Playwright
**Environment Variables**:
- `PLAYWRIGHT_BROWSERS_PATH`: Path to browser binaries (optional)
- `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD`: Set to `1` to skip browser download (optional)
**Authentication Requirements**:
- None for local browser automation
- Website-specific authentication for remote website testing (handled by AI-OS)
**Network Requirements**:
- Localhost access for browser automation
- Outbound network access for remote website testing
- Firewall rules allowing outbound HTTP/HTTPS for website testing (if remote testing)
**Software Requirements**:
- Node.js environment (for Playwright execution)
- Compatible browser binaries (Chromium, Firefox, WebKit) or ability to download them
- No client-side software required for AI-OS integration (uses standard subprocess)
**Hardware Requirements**:
- System capable of running browser automation
- Memory sufficient for browser instances and AI-OS operation
- No specific hardware requirements beyond standard system capability
**Mock vs Real Mode**:
- **Mock Mode**: Automatic when Playwright/browser unavailable or invalid
- **Real Mode**: Requires Playwright installation and accessible browser binaries
**Gated Real-Operational Tests**:
- Requires `AIOS_REAL_INTEGRATION_ENABLED=1` and verified Playwright resources
- Tests actual Playwright installation, browser automation fidelity, and test execution accuracy
**Validation and Readiness**:
- Validate Playwright installation accessibility
- Validate browser binaries accessibility and compatibility
- Integration framework tests Playwright availability before enabling real mode
**Deprecation and Alternates**:
- No planned deprecation for Playwright integration
- Alternative browser automation systems could be added in future versions
- Local agent testing always available as fallback

#### Agent Reach
**Required for**: Communication and information gathering
**User Must Provide**: None (uses standard AI-OS Agent Reach framework)
**Environment Variables**: None
**Authentication Requirements**: None (uses AI-OS internal authentication when needed)
**Network Requirements**:
- Outbound network access for information gathering (HTTP/HTTPS, etc.)
- Firewall rules allowing outbound network access for information gathering
**Software Requirements**: None (built into AI-OS)
**Hardware Requirements**:
- Network connectivity sufficient for information gathering requests
- No specific hardware requirements beyond standard network capability
**Mock vs Real Mode**:
- **Mock Mode**: Automatic when network access unavailable or invalid
- **Real Mode**: Requires network access for information gathering
**Gated Real-Operational Tests**:
- Requires `AIOS_REAL_INTEGRATION_ENABLED=1` and verified network access
- Tests actual network access, information gathering fidelity, and communication accuracy
**Validation and Readiness**:
- Validate network access for information gathering
- Validate firewall rules allow outbound network access for information gathering
- Integration framework tests network access before enabling real mode
**Deprecation and Alternates**:
- No planned deprecation for Agent Reach integration
- Alternative information gathering systems could be added in future versions
- Local knowledge always available as fallback

#### FreeLLMAPI
**Required for**: Local LLM inference for bounded AI tasks
**User Must Provide**:
- Local LLM installation accessible to AI-OS
- Compatible LLM model files for inference
**Environment Variables**:
- `FREELLM_API_URL`: Local LLM API URL (optional, defaults to local endpoint)
- `FREELLM_MODEL_PATH`: Path to LLM model files (optional)
- `FREELLM_MODEL_NAME`: LLM model name to use for inference (optional)
**Authentication Requirements**:
- None for local LLM inference
- Model-specific authentication for remote LLM services (handled by AI-OS)
**Network Requirements**:
- Localhost access for local LLM inference
- Outbound network access for remote LLM services
- Firewall rules allowing outbound HTTP/HTTPS for LLM services (if remote)
**Software Requirements**:
- Local LLM installation (llama.cpp, Hugging Face Transformers, etc.)
- Compatible LLM model files in supported format (GGUF, etc.)
- No client-side software required for AI-OS integration (uses standard subprocess/API)
**Hardware Requirements**:
- System capable of running LLM inference
- Memory sufficient for LLM model and AI-OS operation
- Processing capability sufficient for LLM inference
- No specific hardware requirements beyond standard system capability
**Mock vs Real Mode**:
- **Mock Mode**: Automatic when LLM unavailable or invalid
- **Real Mode**: Requires LLM installation and accessible model files
**Gated Real-Operational Tests**:
- Requires `AIOS_REAL_INTEGRATION_ENABLED=1` and verified LLM resources
- Tests actual LLM installation, inference fidelity, and task execution accuracy
**Validation and Readiness**:
- Validate LLM installation accessibility
- Validate LLM model files accessibility and compatibility
- Integration framework tests LLM availability before enabling real mode
**Deprecation and Alternates**:
- No planned deprecation for FreeLLMAPI integration
- Alternative LLM systems could be added in future versions
- Local rule-based processing always available as fallback

#### Notion
**Required for**: Structured knowledge and database capabilities
**User Must Provide**:
- Notion integration token (from Notion Integrations → Develop)
- Optional: Notion workspace ID or page ID for specific targeting
**Environment Variables**:
- `NOTION_INTEGRATION_TOKEN`: Notion integration token
- `NOTION_WORKSPACE_ID`: Notion workspace ID (optional)
- `NOTION_PAGE_ID`: Notion page ID (optional)
**Authentication Requirements**:
- Integration token authentication via HTTP header (`Authorization: Bearer <token>`)
- Notion workspace must grant integration access to specified resources
**Network Requirements**:
- HTTPS access to Notion API endpoint (`https://api.notion.com`)
- Outbound network access to Notion API endpoints
- Firewall rules allowing outbound HTTPS to api.notion.com
**Software Requirements**:
- Compatible web browser for Notion workspace access (optional)
- No client-side software required for AI-OS integration (uses standard HTTP/HTTPS)
**Hardware Requirements**:
- Network connectivity sufficient for Notion API calls
- No specific hardware requirements beyond standard network capability
**Mock vs Real Mode**:
- **Mock Mode**: Automatic when Notion credentials unavailable or invalid
- **Real Mode**: Requires valid Notion integration token
**Gated Real-Operational Tests**:
- Requires `AIOS_REAL_INTEGRATION_ENABLED=1` and verified Notion credentials
- Tests actual Notion connectivity, authentication, and operation fidelity
**Validation and Readiness**:
- Validate Notion integration token format and validity
- Optional: Validate Notion workspace ID and page ID format and validity
- Integration framework tests Notion connectivity before enabling real mode
**Deprecation and Alternates**:
- No planned deprecation for Notion integration
- Alternative knowledge systems could be added in future versions
- Local file system knowledge persistence always available as fallback

#### Graphify
**Required for**: Relationship and knowledge graph processing
**User Must Provide**:
- Graphify installation accessible to AI-OS
- Optional: Graphify server URL and credentials for remote operation
**Environment Variables**:
- `GRAPHIFY_INSTALLATION_PATH`: Path to Graphify installation (optional)
- `GRAPHIFY_SERVER_URL`: Graphify server URL (optional, for remote operation)
- `GRAPHIFY_USERNAME`: Graphify username (optional, for remote authentication)
- `GRAPHIFY_PASSWORD`: Graphify password (optional, for remote authentication)
**Authentication Requirements**:
- None for local Graphify operation
- Username/password authentication for remote Graphify server (if remote URL provided)
**Network Requirements**:
- Local file system access to Graphify installation
- Optional: Network access to Graphify server URL (if remote URL provided)
- For remote Graphify: firewall rules allowing Graphify protocol access
**Software Requirements**:
- Graphify installation accessible to AI-OS
- Optional: Graphify server installation and accessibility (if remote URL provided)
- No client-side software required for AI-OS integration (uses direct file system/subprocess)
**Hardware Requirements**:
- Local file system access sufficient for Graphify operation
- Optional: System capable of running Graphify server (if remote URL provided)
- No specific hardware requirements beyond standard system capability
**Mock vs Real Mode**:
- **Mock Mode**: Automatic when Graphify unavailable or invalid
- **Real Mode**: Requires Graphify installation accessible to AI-OS
**Gated Real-Operational Tests**:
- Requires `AIOS_REAL_INTEGRATION_ENABLED=1` and verified Graphify resources
- Tests actual Graphify installation, operation fidelity, and knowledge graph processing accuracy
**Validation and Readiness**:
- Validate Graphify installation accessibility
- Optional: Validate Graphify server URL accessibility and credentials
- Integration framework tests Graphify availability before enabling real mode
**Deprecation and Alternates**:
- No planned deprecation for Graphify integration
- Alternative knowledge graph systems could be added in future versions
- Local file system knowledge processing always available as fallback

#### Claude-Mem
**Required for**: AI agent memory and knowledge storage
**User Must Provide**:
- Claude-Mem installation accessible to AI-OS
- Claude-Mem server URL and credentials for remote operation
**Environment Variables**:
- `CLAUDE_MEM_INSTALLATION_PATH`: Path to Claude-Mem installation (optional)
- `CLAUDE_MEM_SERVER_URL`: Claude-Mem server URL (optional, for remote operation)
- `CLAUDE_MEM_USERNAME`: Claude-Mem username (optional, for remote authentication)
- `CLAUDE_MEM_PASSWORD`: Claude-Mem password (optional, for remote authentication)
**Authentication Requirements**:
- None for local Claude-Mem operation
- Username/password authentication for remote Claude-Mem server (if remote URL provided)
**Network Requirements**:
- Local file system access to Claude-Mem installation
- Optional: Network access to Claude-Mem server URL (if remote URL provided)
- For remote Claude-Mem: firewall rules allowing Claude-Mem protocol access
**Software Requirements**:
- Claude-Mem installation accessible to AI-OS
- Optional: Claude-Mem server installation and accessibility (if remote URL provided)
- No client-side software required for AI-OS integration (uses direct file system/subprocess)
**Hardware Requirements**:
- Local file system access sufficient for Claude-Mem operation
- Optional: System capable of running Claude-Mem server (if remote URL provided)
- No specific hardware requirements beyond standard system capability
**Mock vs Real Mode**:
- **Mock Mode**: Automatic when Claude-Mem unavailable or invalid
- **Real Mode**: Requires Claude-Mem installation accessible to AI-OS
**Gated Real-Operational Tests**:
- Requires `AIOS_REAL_INTEGRATION_ENABLED=1` and verified Claude-Mem resources
- Tests actual Claude-Mem installation, operation fidelity, and memory/knowledge processing accuracy
**Validation and Readiness**:
- Validate Claude-Mem installation accessibility
- Optional: Validate Claude-Mem server URL and credentials accessibility
- Integration framework tests Claude-Mem availability before enabling real mode
**Deprecation and Alternates**:
- No planned deprecation for Claude-Mem integration
- Alternative memory systems could be added in future versions
- Local agent memory always available as fallback

## Environment Variables Summary

### Persistence
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_ANON_KEY`: Supabase anon/public key
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key (optional)

### Execution
- `N8N_BASE_URL`: n8n instance URL
- `N8N_API_KEY`: n8n API key

### Knowledge
- `OBSIDIAN_VAULT_PATH`: Absolute path to Obsidian vault directory
- `OBSIDIAN_GIT_REMOTE_URL`: Remote Git repository URL (optional)

### UI
- `DASHBOARD_ENABLED`: Set to `1` to enable dashboard (optional, defaults to enabled)
- `DASHBOARD_HOST`: Dashboard host (optional, defaults to localhost)
- `DASHBOARD_PORT`: Dashboard port (optional, defaults to 3000)
- `DASHBOARD_AUTH_ENABLED`: Set to `1` to enable dashboard authentication (optional)
- `DASHBOARD_USERNAME`: Dashboard username (optional, if authentication enabled)
- `DASHBOARD_PASSWORD`: Dashboard password (optional, if authentication enabled)

### Communication
- `PLAYWRIGHT_BROWSERS_PATH`: Path to browser binaries (optional)
- `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD`: Set to `1` to skip browser download (optional)
- `FREELLM_API_URL`: Local LLM API URL (optional)
- `FREELLM_MODEL_PATH`: Path to LLM model files (optional)
- `FREELLM_MODEL_NAME`: LLM model name to use for inference (optional)
- `NOTION_INTEGRATION_TOKEN`: Notion integration token
- `NOTION_WORKSPACE_ID`: Notion workspace ID (optional)
- `NOTION_PAGE_ID`: Notion page ID (optional)
- `GRAPHIFY_INSTALLATION_PATH`: Path to Graphify installation (optional)
- `GRAPHIFY_SERVER_URL`: Graphify server URL (optional)
- `GRAPHIFY_USERNAME`: Graphify username (optional)
- `GRAPHIFY_PASSWORD`: Graphify password (optional)
- `CLAUDE_MEM_INSTALLATION_PATH`: Path to Claude-Mem installation (optional)
- `CLAUDE_MEM_SERVER_URL`: Claude-Mem server URL (optional)
- `CLAUDE_MEM_USERNAME`: Claude-Mem username (optional)
- `CLAUDE_MEM_PASSWORD`: Claude-Mem password (optional)

## Authentication Requirements Summary

### Supabase
- Anon/public key for client-side operations
- Service role key for admin operations (AI-OS controlled)

### n8n
- API key via HTTP header (`X-N8N-API-KEY`)

### Obsidian + Obsidian Git
- File system access to vault directory
- Git access to vault directory
- Optional: Remote Git repository authentication

### AI-OS Dashboard
- Optional: Username/password authentication
- Optional: Token-based authentication

### Playwright
- Website-specific authentication for remote testing (AI-OS handled)

### Agent Reach
- Uses AI-OS internal authentication when needed

### FreeLLMAPI
- Model-specific authentication for remote services (AI-OS handled)

### Notion
- Integration token via HTTP header (`Authorization: Bearer <token>`)

### Graphify
- Optional: Username/password for remote server authentication

### Claude-Mem
- Optional: Username/password for remote server authentication

## Network Requirements Summary

### Supabase
- HTTPS access to Supabase project URL
- Outbound network access to Supabase API endpoints

### n8n
- HTTP/HTTPS access to n8n instance URL
- Outbound network access to n8n API endpoints

### Obsidian + Obsidian Git
- Local file system access to Obsidian vault directory
- Optional: Network access to remote Git repository

### AI-OS Dashboard
- Localhost access (shared execution environment) OR network access with firewall rules

### Playwright
- Localhost access for browser automation
- Outbound network access for remote website testing

### Agent Reach
- Outbound network access for information gathering

### FreeLLMAPI
- Localhost access for local LLM inference
- Outbound network access for remote LLM services

### Notion
- HTTPS access to Notion API endpoint
- Outbound network access to Notion API endpoints

### Graphify
- Local file system access to Graphify installation
- Optional: Network access to Graphify server URL

### Claude-Mem
- Local file system access to Claude-Mem installation
- Optional: Network access to Claude-Mem server URL

## Software Requirements Summary

### Supabase
- Compatible web browser for dashboard access (optional)

### n8n
- Compatible web browser for interface access (optional)
- n8n instance version 0.200.0 or later

### Obsidian + Obsidian Git
- Obsidian application installed and accessible
- Git installed and accessible in system PATH

### AI-OS Dashboard
- Compatible web browser (Chrome, Firefox, Safari, Edge, etc.)
- Optional: Dashboard client application

### Playwright
- Node.js environment
- Compatible browser binaries (Chromium, Firefox, WebKit) or ability to download them

### Agent Reach
- None (built into AI-OS)

### FreeLLMAPI
- Local LLM installation (llama.cpp, Hugging Face Transformers, etc.)
- Compatible LLM model files in supported format

### Notion
- Compatible web browser for workspace access (optional)

### Graphify
- Graphify installation accessible to AI-OS
- Optional: Graphify server installation and accessibility

### Claude-Mem
- Claude-Mem installation accessible to AI-OS
- Optional: Claude-Mem server installation and accessibility

## Hardware Requirements Summary

### Supabase
- Network connectivity sufficient for API calls

### n8n
- Network connectivity sufficient for API calls
- Host machine meeting n8n system requirements

### Obsidian + Obsidian Git
- Local file system access sufficient for vault operations
- Disk space sufficient for vault and Git history
- Git executable accessible in system PATH

### AI-OS Dashboard
- Device capable of running modern web browser
- Display sufficient for dashboard interface
- Input device for dashboard interaction

### Playwright
- System capable of running browser automation
- Memory sufficient for browser instances
- Processing capability sufficient for browser automation

### Agent Reach
- Network connectivity sufficient for information gathering

### FreeLLMAPI
- System capable of running LLM inference
- Memory sufficient for LLM model
- Processing capability sufficient for LLM inference

### Notion
- Network connectivity sufficient for API calls

### Graphify
- Local file system access sufficient for operation
- Optional: System capable of running Graphify server

### Claude-Mem
- Local file system access sufficient for operation
- Optional: System capable of running Claude-Mem server

## Mock vs Real Mode Distinctions

### Mock Mode Characteristics
- **Automatic Activation**: Activates when real mode resources unavailable or invalid
- **In-Memory Simulation**: Uses in-memory simulators that mimic real system behavior
- **Structured Responses**: Returns structured responses matching real system formats
- **Behavioral Fidelity**: Simulates realistic behavior including delays, errors, and edge cases
- **Boundary Testing**: Enables testing of boundary conditions and error scenarios
- **Learning Extraction**: Enables extraction of validated learning from simulated outcomes
- **No External Dependencies**: Eliminates need for external system configuration or access
- **Consistent Behavior**: Provides consistent, predictable behavior for testing
- **Resource Isolation**: Eliminates resource usage from external systems
- **Security Isolation**: Eliminates security risks from external system access
- **Cost Elimination**: Eliminates costs associated with external system usage
- **Availability**: Always available regardless of external system status
- **Development Focus**: Enables development and testing without external dependencies

### Real Mode Characteristics
- **Resource-Dependent**: Requires verified user resources for activation
- **Actual System Integration**: Connects to and uses actual external systems
- **Real-World Behavior**: Exhibits actual external system behavior including performance characteristics
- **Proven Integration**: Validates actual integration with real external systems
- **Performance Characteristics**: Exhibits actual external system performance characteristics
- **Real Error Handling**: Handles actual external system errors and failure modes
- **Real Network Characteristics**: Experiences actual network characteristics and latency
- **Real Resource Usage**: Consumes actual resources from external systems
- **Real Security Considerations**: Addresses actual external system security considerations
- **Real Cost Considerations**: Incurs actual costs associated with external system usage
- **Availability Dependent**: Availability depends on external system status and accessibility
- **Production Focus**: Enables production operation with real external systems
- **User Validation**: Requires user to provide and validate actual resources

## Gated Real-Operational Tests

### Requirements
- **Feature Flag**: `AIOS_REAL_INTEGRATION_ENABLED=1` must be set
- **Resource Verification**: User resources verified for readiness and accessibility
- **Environment Compatibility**: Test environment compatible with user resources
- **Integration Testing**: Tests actual integration with real external systems
- **Fidelity Validation**: Validates actual integration fidelity and accuracy
- **Performance Measurement**: Measures actual performance characteristics
- **Resource Usage Measurement**: Measures actual resource usage from external systems
- **Error Handling Validation**: Validates actual error handling and failure modes
- **Network Characteristics**: Experiences actual network characteristics and latency
- **Security Validation**: Validates actual security considerations and controls
- **Cost Consideration**: Accounts for actual costs associated with external system usage
- **Learning Extraction**: Extracts validated learning from real integration results
- **Authority Preservation**: Verifies AI-OS remains sole governance, verification, and decision-making authority
- **Bounded Resource Compliance**: Verifies external systems operate as bounded resources under AI-OS control

### Validation Process
1. **Pre-Test Validation**: Validates user resources before test execution
2. **Resource Readiness**: Confirms user resources are ready and accessible
3. **Environment Setup**: Sets up test environment for user resources
4. **Integration Testing**: Tests actual integration with real external systems
5. **Fidelity Validation**: Validates actual integration fidelity and accuracy
6. **Performance Measurement**: Measures actual performance characteristics
7. **Resource Usage Measurement**: Measures actual resource usage from external systems
8. **Error Handling Validation**: Validates actual error handling and failure modes
9. **Network Validation**: Experiences actual network characteristics and latency
10. **Security Validation**: Validates actual security considerations and controls
11. **Cost Validation**: Accounts for actual costs associated with external system usage
12. **Learning Extraction**: Extracts validated learning from real integration results
13. **Authority Check**: Verifies AI-OS remains sole governance, verification, and decision-making authority
14. **Resource Compliance Check**: Verifies external systems operate as bounded resources under AI-OS control
15. **Post-Test Cleanup**: Cleans up resources after test execution
16. **Environment Reset**: Resets test environment after test execution
17. **Result Reporting**: Reports test results for decision making and learning
18. **Escalation Process**: Escalates persistent failures to appropriate authority
19. **Retry Process**: Retries tests if flaky or inconclusive (within bounds)
20. **Confirmation Process**: Confirms test results before proceeding

## Validation and Readiness

### Pre-Use Validation
Users should validate their resources before attempting real-mode operation:
1. **Resource Availability**: Confirm resources are available and accessible
2. **Credential Validity**: Confirm credentials are valid and not expired
3. **Access Permissions**: Confirm necessary access permissions are granted
4. **Network Connectivity**: Confirm network connectivity to required endpoints
5. **Software Compatibility**: Confirm software versions are compatible
6. **Hardware Suitability**: Confirm hardware meets minimum requirements
7. **Environment Variables**: Confirm environment variables are correctly set
8. **Integration Framework**: Confirm integration framework is ready for real mode
9. **Security Validation**: Confirm security controls are properly configured
10. **Authority Preservation**: Confirm AI-OS authority preservation mechanisms are active
11. **Bounded Resource Compliance**: Confirm bounded resource compliance mechanisms are active
12. **Documentation Review**: Review integration documentation for correct usage
13. **Test Validation**: Run validation tests to confirm resource readiness
14. **Learning Preparation**: Prepare to extract validated learning from real-mode operation
15. **Escalation Preparation**: Prepare to escalate issues to appropriate authority
16. **Retry Preparedness**: Prepare to retry operations if flaky or inconclusive
17. **Confirmation Preparedness**: Prepare to confirm successful operations

### Readiness Indicators
Indicators that resources are ready for real-mode operation:
- **Connectivity**: Resources respond to connection attempts
- **Authentication**: Authentication succeeds with provided credentials
- **Authorization**: Authorization succeeds for requested operations
- **Network**: Network connectivity is stable and sufficient
- **Software**: Software versions are compatible and functional
- **Hardware**: Hardware meets requirements and functions correctly
- **Environment**: Environment variables are correctly set and accessible
- **Integration**: Integration framework reports readiness for real mode
- **Security**: Security controls are properly configured and functional
- **Authority**: AI-OS authority preservation mechanisms are active and functional
- **Bounds**: Bounded resource compliance mechanisms are active and functional
- **Documentation**: Integration documentation is understood and applicable
- **Testing**: Validation tests pass and indicate resource readiness
- **Learning**: Prepared to extract validated learning from operation
- **Escalation**: Prepared to escalate issues to appropriate authority
- **Retry**: Prepared to retry operations if flaky or inconclusive
- **Confirmation**: Prepared to confirm successful operations

## Determining Mandatory vs Optional

### For v1 of M13 Milestone: OPTIONAL for All External Resources
All external user resources are **OPTIONAL** for v1 of the M13 milestone because:
1. AI-OS can operate in mock mode without any external user resources
2. Core AI-OS functionality does not depend on external user resources
3. All M0-M12 functionality verified without external user resource dependency
4. External user resources enhance capabilities but don't enable new core functionality
5. Users may prefer to operate in mock mode or use alternative resources
6. Local fallbacks always available for persistence, execution, knowledge, etc.
7. AI-OS retains full authority and capability in mock mode
8. Mock mode provides sufficient functionality for development and testing
9. Real mode enhances fidelity but doesn't change AI-OS authority structure
10. Learning from real mode enhances but doesn't change core AI-OS operation

### Conditions for Making Resources More Central
Resources could gain increased importance when:
1. Real-world fidelity and accuracy become necessary for validation
2. Performance characteristics require actual external system behavior
3. Resource usage patterns need to be measured in real systems
4. Error handling and failure modes require actual external system behavior
5. Network characteristics and latency need to be experienced in real systems
6. Security considerations require actual external system security validation
7. Cost considerations need to be evaluated in real-world scenarios
8. Learning from actual external system behavior becomes valuable
9. User experience requires actual external system interaction
10. Compliance requirements necessitate real-world validation and testing
11. Integration accuracy needs to be validated with real external systems
12. Data fidelity requirements necessitate actual external system data handling
13. Communication effectiveness needs to be measured with real external systems
14. Authentication effectiveness needs to be validated with real external systems
15. Authorization effectiveness needs to be validated with real external systems
16. Secret handling effectiveness needs to be validated with real external systems
17. Zeroization effectiveness needs to be validated with real external systems
18. Bounds enforcement effectiveness needs to be validated with real external systems
19. Provenance preservation effectiveness needs to be validated with real external systems
20. Authority preservation effectiveness needs to be validated with real external systems

However, even with increased usage, AI-OS would retain:
- Complete authority over governance, verification, and decision-making
- Clear separation between AI-OS authority and resource functionality
- Ability to implement equivalent functionality through other mechanisms
- Mandatory AI-OS evaluation of all resource results and outputs
- Resources remaining as bounded resources under AI-OS control
- Mock mode always available as fallback for development and testing
- Local fallbacks always available for core functionality
- AI-OS always able to operate as an authoritative autonomous system

## Summary

The M13 User Resource Checklist provides the definitive list of what users must provide for real-mode operation of AI-OS M13 with all external integrations while preserving AI-OS as the sole governance, verification, and decision-making authority. Through clear resource categories, specific requirements for each integration, environment variable specifications, authentication requirements, network requirements, software requirements, hardware requirements, mock vs real mode distinctions, gated real-operational test requirements, validation and readiness indicators, and deprecation/alternates information, the checklist enables users to properly prepare their resources for real-mode operation. The checklist ensures that AI-OS remains the sole authority while specifying exactly what users need to provide for enhanced fidelity and real-world validation.