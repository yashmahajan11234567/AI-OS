# AI-OS Repository Ecosystem Specification

## Document Overview

This document provides a comprehensive and authoritative catalog of all repositories that form part of the AI-OS ecosystem as defined by the Hermes Kernel v1.0 Architecture Specification (Parts 1-15). It classifies each repository according to its role in the AI-OS architectural framework and describes its purpose, architectural role, implementation role, lifecycle status, specification status, production readiness, conformance requirements, extension points, dependencies, and related repositories.

The document distinguishes between the following architectural categories:
- **Core Architecture**: Frozen specification defining what AI-OS must be (Parts 1-15)
- **Core Implementation**: Reference runtime implementing the Hermes Kernel v1.0 specification
- **AI Agency**: Specialized service for AI agent lifecycle management and governance (Core Manager)
- **Reference Implementations**: Authoritative implementations of core capabilities (Core Managers)
- **External Integrations**: Third-party systems integrated via defined architectural contracts
- **MCP Integrations**: Model Context Protocol server/client implementations for tool independence
- **Skills Integrations**: Reusable capability packages implementing the SkillManager contract
- **Development Tools**: Tools used in AI-OS development, maintenance, and quality assurance
- **Evaluation Tools**: Frameworks for testing, validation, and benchmarking AI-OS capabilities

Each repository entry includes standardized architectural fields to enable consistent comparison, dependency analysis, conformance validation, and architectural governance:
- **Purpose**: Clear statement of why the repository exists in the ecosystem
- **Architectural Role**: How the repository fulfills architectural contracts and principles
- **Implementation Role**: Technical responsibilities and capabilities provided
- **Lifecycle Status**: Current phase in the repository lifecycle (specified, implemented, deprecated, etc.)
- **Specification Status**: Level of conformance to AI-OS architectural specification
- **Production Readiness**: Assessment of suitability for production deployment
- **Conformance Requirements**: Specific architectural requirements the repository must satisfy
- **Extension Points**: Defined points where the repository can be extended or customized
- **Dependencies**: Repositories, specifications, or systems this repository relies on
- **Related Repositories**: Repositories that interact with or depend on this repository
- **Advantages**: Benefits of including this repository in the AI-OS ecosystem
- **Limitations**: Constraints, trade-offs, or challenges associated with this repository
- **Future Plans**: Planned enhancements, evolutions, or deprecations
- **Current Status**: Present state of development, implementation, or integration
- **Historical Notes**: Evolution of the repository through AI-OS architecture history

## Classification System

Each repository in the AI-OS ecosystem is classified into one of the following mutually exclusive categories:

1. **Core Architecture Repository** - The frozen specification (Parts 1-15) that defines what AI-OS must be; contains no executable code
2. **Core Implementation Repository** - The reference runtime implementation (ai-os/Hermes) that implements the Core Architecture Specification
3. **AI Agency** - Specialized service for AI agent lifecycle management, audit trails, and governance; implements the AI Agency Core Manager
4. **Reference Implementation** - Authoritative implementations of core capabilities (Core Managers excluding AI Agency); implementations of specified interfaces
5. **External Integration** - Third-party systems integrated via defined architectural contracts (e.g., alternative AI agent frameworks, execution providers)
6. **MCP Integration** - Model Context Protocol server implementations that provide standardized tool access; complements the MCPManager Core Manager
7. **Skills Integration** - Reusable capability packages that implement the SkillManager contract; extends AI-OS functionality
8. **Development Tool** - Tools used in AI-OS development, maintenance, and quality assurance; not required for runtime
9. **Evaluation Tool** - Frameworks for testing, validation, and benchmarking AI-OS capabilities and LLM interactions
10. **Optional/Future Integration** - Planned or prospective integrations that are specified in architecture but not yet implemented or categorized

## Repository Catalog

### 1. Core Architecture Repository

#### AI-OS Architecture Specification
- **Purpose**: The authoritative, frozen specification defining the AI-OS Hermes Kernel v1.0 as a complete engineering operating system architecture
- **Architectural Role**: Defines what the system must be and why (not how), establishing contracts that all implementations must follow
- **Implementation Role**: Specification-only - contains architecture documents, principles, decision records, and conformance guidelines; no executable code
- **Lifecycle Status**: Frozen specification
- **Specification Status**: FROZEN - Authoritative Source of Truth
- **Production Readiness**: N/A (specification artifact)
- **Conformance Requirements**: All AI-OS implementations must conform to this specification
- **Extension Points**: Defined throughout the specification for core managers, services, and integrations
- **Dependencies**: None - pure specification artifact
- **Related Repositories**: 
  - Referenced by ai-os reference implementation for conformance validation
  - Used by architects, reviewers, and auditors for compliance checking
  - Basis for Architecture Review Board (ARB) decision-making
  - Defines extension points consumed by all integrations
- **Advantages**:
  - Provides architectural stability and prevents drift from original intent
  - Enables clear communication of design intent across teams
  - Supports automated conformance testing and validation
  - Serves as educational artifact for onboarding new team members
- **Limitations**:
  - Specification and implementation evolve at different rates
  - May lag behind cutting-edge implementation innovations
  - Changes require formal ARB approval process
- **Future Plans**: Continue evolving through formal Architecture Review Board process; Parts 13+ will be added as needed for emerging capabilities
- **Current Status**: FROZEN (Parts 0-12) - Authoritative Source of Truth as of 2026-07-28
- **Location**: `C:\Development\AI-OS\architecture\` (specification documents)
- **Historical Note**: Evolved from the original Hermes-centric architecture to a formal specification to prevent architectural entropy

### 2. Core Implementation Repository

#### ai-os (Hermes Runtime)
- **Purpose**: The reference implementation of the AI-OS Hermes Kernel v1.0 and complete engineering operating system platform
- **Architectural Role**: Implements the Hermes Kernel (orchestration core) and AI-OS Platform as defined in the architecture specification
- **Implementation Role**: Contains all source code in `src/aios/` including kernel components, capability managers, engineering services, facade services, CLI, and extension points
- **Lifecycle Status**: Active development
- **Specification Status**: IMPLEMENTED (working toward v1.0 conformance)
- **Production Readiness**: Development/deployable (v0.1.x)
- **Conformance Requirements**: Must conform to AI-OS Architecture Specification
- **Extension Points**: Plugin system for custom skills, memory backends, MCP transports
- **Dependencies**:
  - Python 3.12+
  - Typer (CLI framework)
  - Rich (terminal formatting)
  - Pydantic (data validation)
  - PyYAML (configuration)
  - Development dependencies (ruff, mypy, pytest)
- **Related Repositories**:
  - Implements contracts defined in AI-OS Architecture repository
  - Consumes extensions via plugin system (custom skills, memory backends, MCP transports)
  - Provides CLI interface for users and automation systems
  - Integrates with external systems via MCP (Model Context Protocol)
- **Advantages**:
  - Production-quality, well-tested reference implementation
  - Demonstrates architectural principles in practice
  - Provides extensibility points for customization
  - Includes built-in observability and recovery mechanisms
- **Limitations**:
  - May contain implementation details not specified in architecture
  - Evolution constrained by specification conformance requirements
- **Future Plans**: Continue implementation toward full v1.0 conformance; migration path defined from v0.1.x to v1.0 target
- **Current Status**: Implementation v0.1.x - Working toward Architecture Target v1.0 conformance
- **Location**: `C:\Development\AI-OS\` (main repository)
- **Historical Note**: Originally referred to as "Hermes Runtime"; represents the ongoing implementation effort

### 3. AI Agency

#### AI Agency Service
- **Purpose**: Specialized service for AI agent lifecycle management, audit trails, and governance mechanisms within AI-OS
- **Architectural Role**: Implements the AI Agency Capability Manager (one of the 9 required Core Managers) that governs AI agent behavior
- **Implementation Role**: Contains AI agent spawning, lifecycle, communication management, resource quotas, permission sandboxing, audit logging, and performance monitoring
- **Lifecycle Status**: Active implementation
- **Specification Status**: IMPLEMENTED (Part of Core Managers)
- **Production Readiness**: Development/deployable (Part of v0.1.x)
- **Conformance Requirements**: Must conform to AI Agency Capability Manager interface in AI-OS Architecture Specification
- **Extension Points**: Governance policies, audit logging mechanisms, trust domains
- **Dependencies**:
  - Hermes Kernel interfaces (EventBus, StateManager, etc.)
  - EventSystem for communication
  - StateManager for persistent agent state
  - ConfigurationSystem for agent policies
- **Related Repositories**:
  - Receives agent requests via EventBus (e.g., `agent.spawn_requested`)
  - Emits audit events (`*_requested`/`*_completed` pairs)
  - Provides global singleton accessor `get_ai_agency_service()`
  - Works with CouncilService for governance decisions
  - Integrates with MemoryService for audit trail storage
- **Advantages**:
  - Provides structured AI governance with human-in-the-loop capabilities
  - Enables audit trails for all AI-influenced decisions
  - Supports configurable autonomy levels based on risk tolerance
  - Implements FinalJudge as mandatory gate for critical operations
- **Limitations**:
  - Adds complexity to agent lifecycle management
  - Requires careful tuning of governance policies
- **Future Plans**: Enhance with more sophisticated audit agents, trust domains, and security scanning capabilities
- **Current Status**: Implemented in core (`src/aios/core/ai_agency.py`) with facade service - Part of Phase 7 completion
- **Historical Note**: Evolved from original AI Agency concept to full governance framework

### 4. Reference Implementations

#### ObservabilityManager
- **Purpose**: Provides industry-standard observability capabilities (metrics, tracing, logging) for AI-OS
- **Architectural Role**: Implements the ObservabilityManager Core Manager providing metrics, tracing, logging, and health checks
- **Implementation Role**: Provides OpenTelemetry-compatible distributed tracing, metrics collection and export, log correlation, and resource instrumentation
- **Lifecycle Status**: Active implementation
- **Specification Status**: IMPLEMENTED (Part of Core Managers)
- **Production Readiness**: Development/deployable (Part of v0.1.x)
- **Conformance Requirements**: Must conform to ObservabilityManager Core Manager interface in AI-OS Architecture Specification
- **Extension Points**: Exporter backends, instrumentation libraries, health check extensions
- **Dependencies**:
  - OpenTelemetry SDK and API
  - Compatible exporters and backends
  - Hermes Kernel interfaces
- **Related Repositories**:
  - Integrates with all components via automatic instrumentation
  - Receives trace context from EventBus events
  - Exports data to configured observability backends (Jaeger, Zipkin, Prometheus, etc.)
  - Provides health check and profiling capabilities
- **Advantages**:
  - Industry standard for observability with rich tooling ecosystem
  - Automatic instrumentation reduces implementation burden
  - Supports correlation across services and systems
  - Built-in as required by architectural principles
- **Limitations**:
  - Can introduce performance overhead
  - Configuration complexity for advanced use cases
  - Potential vendor lock-in with specific exporters
- **Future Plans**: Enhance with AI-driven anomaly detection, predictive scaling, and automated root cause analysis
- **Current Status**: Implemented as Core Manager - Part of the 9 required managers
- **Historical Note**: Evolved from basic logging to full OpenTelemetry integration

#### ModelRouter
- **Purpose**: Provides provider-agnostic LLM capability routing for AI-OS
- **Architectural Role**: Implements the ModelRouter Core Manager providing capability-based LLM provider routing
- **Implementation Role**: Registers LLM providers by capability, performs dynamic capability scoring, manages fallback chains, and monitors provider health
- **Lifecycle Status**: Active implementation
- **Specification Status**: IMPLEMENTED (Part of Core Managers)
- **Production Readiness**: Development/deployable (Part of v0.1.x)
- **Conformance Requirements**: Must conform to ModelRouter Core Manager interface in AI-OS Architecture Specification
- **Extension Points**: Provider capability definitions, custom routing algorithms, health check extensions
- **Dependencies**:
  - LLM provider APIs (Anthropic, OpenSource, etc.)
  - Hermes Kernel interfaces
  - ConfigurationSystem for provider settings
- **Related Repositories**:
  - Receives LLM requests via EventBus from services
  - Routes requests to appropriate providers based on capability requirements
  - Manages provider health, failover, and load balancing
  - Emits LLM completion events via EventBus
- **Advantages**:
  - Achieves vendor independence as required by architectural principles
  - Enables dynamic provider selection based on capabilities
  - Provides fallback chains for reliability
  - Abstracts provider-specific SDKs behind capability interface
- **Limitations**:
  - Requires maintenance of provider capability definitions
  - May introduce latency in provider selection
- **Future Plans**: Enhance with more sophisticated capability scoring and real-time provider performance monitoring
- **Current Status**: Implemented as Core Manager - Part of the 9 required managers
- **Historical Note**: Evolved from basic LLMManager to capability-based ModelRouter

### 5. External Integrations

#### free-claude-code
- **Purpose**: Enables compatibility with and potential replacement of the original Claude Code CLI within AI-OS workflows
- **Architectural Role**: External CLI tool that integrates with AI-OS through standard interfaces (MCP, skills, etc.)
- **Implementation Role**: Modified Claude Code CLI that can operate using AI-OS services as backends
- **Lifecycle Status**: Community-maintained
- **Specification Status**: COMPATIBLE - Referenced in architecture
- **Production Readiness**: Usable (community fork)
- **Conformance Requirements**: Must implement AI-OS standard interfaces (MCP, skills)
- **Extension Points**: Custom skills, MCP integrations
- **Dependencies**:
  - Anthropic Claude API (or compatible)
  - AI-OS MCP servers for tool access
  - Standard input/output interfaces
- **Related Repositories**:
  - Can use AI-OS as backend through MCP integration
  - Integrates with AI-OS skill system for capability extension
  - Consumes AI-OS services via standard APIs
- **Advantages**:
  - Lowers barrier to entry for existing Claude Code users
  - Provides familiar CLI experience
  - Enables gradual migration to AI-OS architecture
  - Leverages existing Claude Code ecosystem
- **Limitations**:
  - May not fully leverage AI-OS architectural advantages
  - Coupled to specific CLI paradigm
  - Dependency on external Claude Code evolution
- **Future Plans**: Enhance bidirectional integration; potentially replace native AI-OS CLI in some contexts
- **Current Status**: Referenced in architecture as compatible execution provider; community-maintained fork
- **Historical Note**: Identified as compatible execution provider in Part 8; architecture explicitly supports vendor independence

#### OpenHands (formerly OpenDevin)
- **Purpose**: Provides alternative AI software engineer agent paradigm for integration with AI-OS
- **Architectural Role**: External AI agent framework that can integrate with AI-OS as underlying platform
- **Implementation Role**: Agent-based software engineering system with its own planning/execution paradigms
- **Lifecycle Status**: Not implemented (referenced only)
- **Specification Status**: REFERENCED - Potential integration
- **Production Readiness**: Not applicable (not implemented)
- **Conformance Requirements**: Must implement standard AI-OS interfaces (MCP, skills)
- **Extension Points**: Custom agent behaviors, skill integrations
- **Dependencies**:
  - LLM API access (compatible with AI-OS ModelRouter)
  - Standard tool execution environment
  - MCP or API interfaces for integration
- **Related Repositories**:
  - Can utilize AI-OS MCP servers for tool access
  - Can consume AI-OS skills as capabilities
  - Potentially use AI-OS as underlying execution platform
- **Advantages**:
  - Brings different perspective on autonomous software engineering
  - Can leverage AI-OS stability and infrastructure
  - Provides alternative to native AI-OS engineering services
  - Expands ecosystem through diversity of approaches
- **Limitations**:
  - May duplicate functionality already in AI-OS services
  - Integration complexity due to different paradigms
  - Requires adaptation layer for full integration
- **Future Plans**: Define clear integration contracts; potentially host as specialized AI agent within AI-OS Agency
- **Current Status**: Referenced in documentation as potential integration; not currently implemented
- **Historical Note**: Evaluated during architecture evolution; recognized as complementary paradigm

#### Continue
- **Purpose**: Provides IDE-integrated AI coding assistant that can utilize AI-OS as backend
- **Architectural Role**: External IDE plugin that integrates with AI-OS through standard APIs
- **Implementation Role**: VS Code/JetBrains extension providing inline code assistance, generation, and editing
- **Lifecycle Status**: Not implemented (referenced only)
- **Specification Status**: REFERENCED - Compatible integration
- **Production Readiness**: Not applicable (not implemented)
- **Conformance Requirements**: Must implement standard AI-OS interfaces (MCP, skills, API endpoints)
- **Extension Points**: Custom language support, IDE-specific features
- **Dependencies**:
  - IDE plugin framework (VS Code, JetBrains, etc.)
  - AI-OS API endpoints (MCP, REST, or direct integration)
  - LLM access (can route through AI-OS ModelRouter)
- **Related Repositories**:
  - Utilizes AI-OS MCP servers for tool access (file operations, search, etc.)
  - Consumes AI-OS skills for specialized capabilities
  - Can route LLM requests through AI-OS ModelRouter
  - Integrates with AI-OS services for context-aware assistance
- **Advantages**:
  - Brings AI-OS capabilities to developers in their native IDE
  - Provides familiar inline assistance experience
  - Leverages AI-OS stability and security
  - Expands AI-OS accessibility through popular extension
- **Limitations**:
  - Dependent on IDE plugin ecosystem stability
  - May not expose full AI-OS architectural capabilities
  - Requires ongoing maintenance for IDE updates
- **Future Plans**: Develop official AI-OS Continue extension; enhance bidirectional context sharing
- **Current Status**: Referenced in documentation as compatible IDE integration; community extensions exist
- **Historical Note**: Mentioned in architecture discussions as compatible execution provider paradigm

#### Cline
- **Purpose**: Provides autonomous coding agent that can integrate with AI-OS infrastructure
- **Architectural Role**: External autonomous coding agent system
- **Implementation Role**: CLI-based autonomous agent for software development tasks
- **Lifecycle Status**: Not implemented (referenced only)
- **Specification Status**: REFERENCED - Compatible execution model
- **Production Readiness**: Not applicable (not implemented)
- **Conformance Requirements**: Must implement standard AI-OS interfaces (MCP, skills)
- **Extension Points**: Custom agent behaviors, tool integrations
- **Dependencies**:
  - LLM API access
  - File system access for project operations
  - Standard input/output interfaces
- **Related Repositories**:
  - Can utilize AI-OS MCP servers for enhanced tool capabilities
  - Potentially integrate with AI-OS skill system
  - Can use AI-OS as execution platform for agent operations
- **Advantages**:
  - Brings state-of-the-art autonomous agent capabilities
  - Can leverage AI-OS stability and security infrastructure
  - Provides alternative interaction paradigm
  - Expands ecosystem through diversity
- **Limitations**:
  - May not fully utilize AI-OS architectural advantages
  - Integration requires adaptation layer
  - Dependent on external project evolution
- **Future Plans**: Evaluate for hosting as specialized AI agent within AI-OS Agency
- **Current Status**: Referenced as compatible execution model; not currently integrated
- **Historical Note**: Evaluated during architecture discussions; recognized as compatible agent paradigm

#### Aider
- **Purpose**: Provides terminal-based AI pair programming that can utilize AI-OS services
- **Architectural Role**: External AI pair programming tool
- **Implementation Role**: Terminal-based AI assistant for code editing and pair programming
- **Lifecycle Status**: Not implemented (referenced only)
- **Specification Status**: REFERENCED - Compatible tool
- **Production Readiness**: Not applicable (not implemented)
- **Conformance Requirements**: Must implement standard AI-OS interfaces (MCP, skills)
- **Extension Points**: Custom command integrations, skill-based enhancements
- **Dependencies**:
  - Terminal environment
  - LLM API access (can route through AI-OS)
  - Git and standard development tools
- **Related Repositories**:
  - Can utilize AI-OS MCP servers for file operations and search
  - Can consume AI-OS skills for specialized capabilities
  - Can route LLM requests through AI-OS ModelRouter
  - Integrates with AI-OS services for context awareness
- **Advantages**:
  - Brings familiar terminal-based pair programming experience
  - Leverages AI-OS stability and security
  - Provides low-friction entry point to AI-OS capabilities
  - Strong existing community and adoption
- **Limitations**:
  - Terminal-only interface limits some capabilities
  - May not expose full AI-OS architectural features
  - Requires maintenance for compatibility
- **Future Plans**: Develop official AI-OS integration; enhance bidirectional context sharing
- **Current Status**: Referenced in documentation as compatible tool; community integrations possible
- **Historical Note**: Discussed as compatible execution provider in architecture evolution

#### SWE-Agent
- **Purpose**: Provides specialized software engineering agent benchmark and framework
- **Architectural Role**: External SWE agent framework and benchmark suite
- **Implementation Role**: Research framework for evaluating AI agents on software engineering tasks
- **Lifecycle Status**: Not implemented (referenced only)
- **Specification Status**: REFERENCED - Evaluation framework
- **Production Readiness**: Not applicable (not implemented)
- **Conformance Requirements**: Must implement standard AI-OS interfaces for integration
- **Extension Points**: Custom benchmark tasks, evaluation metrics
- **Dependencies**:
  - LLM API access
  - Standard software engineering environments
  - Benchmark task definitions
- **Related Repositories**:
  - Can utilize AI-OS as execution platform for SWE-Agent tasks
  - Can benchmark AI-OS engineering services against SWE-Agent tasks
  - Potentially integrate AI-OS as specialized SWE agent
- **Advantages**:
  - Provides standardized benchmark for AI software engineering capability
  - Enables objective comparison of different approaches
  - Validates AI-OS against established research benchmarks
  - Drives improvement through measurable outcomes
- **Limitations**:
  - Research-focused; may not represent production needs
  - Benchmark tasks may not cover full SDLC
  - Requires adaptation for production use
- **Future Plans**: Host official SWE-Agent benchmark for AI-OS; use for validation and improvement
- **Current Status**: Referenced in documentation as evaluation framework; not currently integrated
- **Historical Note**: Evaluated as potential validation mechanism for AI-OS capabilities

#### AutoGen
- **Purpose**: Provides multi-agent conversation framework that can integrate with AI-OS
- **Architectural Role**: External multi-agent conversation and collaboration framework
- **Implementation Role**: Framework for building LLM-powered multi-agent applications
- **Lifecycle Status**: Not implemented (referenced only)
- **Specification Status**: REFERENCED - Compatible framework
- **Production Readiness**: Not applicable (not implemented)
- **Conformance Requirements**: Must implement standard AI-OS interfaces (MCP, skills)
- **Extension Points**: Custom agent capabilities, conversation patterns
- **Dependencies**:
  - LLM API access
  - Standard messaging/communication interfaces
  - Agent conversation frameworks
- **Related Repositories**:
  - Can utilize AI-OS MCP servers as tools for agents
  - Can host AI-OS services as agents within AutoGen
  - Can integrate AI-OS skill system as agent capabilities
  - Potentially use AI-OS as underlying platform
- **Advantages**:
  - Brings sophisticated multi-agent conversation capabilities
  - Enables complex agent collaboration patterns
  - Can leverage AI-OS stability and security
  - Provides research and experimentation platform
- **Limitations**:
  - May duplicate AI-OS Agency functionality
  - Integration complexity due to different paradigms
  - Requires adaptation layer
- **Future Plans**: Evaluate for hosting specialized AutoGen agents within AI-OS
- **Current Status**: Referenced in documentation as compatible framework; not currently integrated
- **Historical Note**: Discussed during architecture evolution as compatible multi-agent approach

#### CrewAI
- **Purpose**: Provides role-based AI agent framework for specialized agent creation
- **Architectural Role**: External role-based AI agent framework
- **Implementation Role**: Framework for creating specialized AI agents with defined roles and goals
- **Lifecycle Status**: Not implemented (referenced only)
- **Specification Status**: REFERENCED - Compatible framework
- **Production Readiness**: Not applicable (not implemented)
- **Conformance Requirements**: Must implement standard AI-OS interfaces (MCP, skills)
- **Extension Points**: Custom role definitions, agent capabilities, tool integrations
- **Dependencies**:
  - LLM API access
  - Standard agent communication interfaces
  - Role definition frameworks
- **Related Repositories**:
  - Can utilize AI-OS MCP servers as tools for CrewAI agents
  - Can host AI-OS services as specialized agents within CrewAI
  - Can integrate AI-OS skill system as agent capabilities
  - Potentially use AI-OS as underlying execution platform
- **Advantages**:
  - Brings structured role-based agent paradigm
  - Enables creation of specialized domain expert agents
  - Can leverage AI-OS stability and infrastructure
  - Provides alternative to native AI-OS Agency approach
- **Limitations**:
  - May not fully utilize AI-OS architectural advantages
  - Integration requires careful boundary definition
  - Dependent on external project maintenance
- **Future Plans**: Evaluate for hosting specialized CrewAI agents within AI-OS Agency
- **Current Status**: Referenced in documentation as compatible framework; not currently integrated
- **Historical Note**: Evaluated during architecture discussions as compatible agent framework

#### LangGraph
- **Purpose**: Provides stateful multi-agent orchestration framework for complex workflows
- **Architectural Role**: External stateful multi-agent orchestration framework
- **Implementation Role**: Library for building stateful, multi-actor applications with LLMs
- **Lifecycle Status**: Not implemented (referenced only)
- **Specification Status**: REFERENCED - Compatible framework
- **Production Readiness**: Not applicable (not implemented)
- **Conformance Requirements**: Must implement standard AI-OS interfaces (WorkflowManager, skills)
- **Extension Points**: Custom node types, execution strategies, persistence backends
- **Dependencies**:
  - LLM API access
  - Standard state management interfaces
  - Graph-based workflow frameworks
- **Related Repositories**:
  - Can utilize AI-OS WorkflowManager as execution backend
  - Can enhance AI-OS workflows with LangGraph capabilities
  - Potentially integrate as specialized workflow engine within AI-OS
- **Advantages**:
  - Brings sophisticated stateful workflow orchestration
  - Enables complex conditional and iterative workflows
  - Can leverage AI-OS stability and reliability
  - Provides research and experimentation platform
- **Limitations**:
  - May duplicate AI-OS WorkflowManager functionality
  - Integration complexity due to different paradigms
  - Requires adaptation layer
- **Future Plans**: Evaluate for enhancing AI-OS WorkflowManager with LangGraph capabilities
- **Current Status**: Referenced in documentation as compatible framework; not currently integrated
- **Historical Note**: Discussed during architecture evolution as compatible workflow approach

#### Semantic Kernel
- **Purpose**: Provides Microsoft-backed LLM orchestration SDK with skills and plugins
- **Architectural Role**: External LLM orchestration SDK with skills/plugins architecture
- **Implementation Role**: SDK for integrating LLMs into applications with skills, planners, and connectors
- **Lifecycle Status**: Not implemented (referenced only)
- **Specification Status**: REFERENCED - Compatible SDK
- **Production Readiness**: Not applicable (not implemented)
- **Conformance Requirements**: Must implement standard AI-OS interfaces (MCP, skills)
- **Extension Points**: Custom skills, planners, connectors
- **Dependencies**:
  - LLM API access
  - Standard SDK interfaces
  - Skill and plugin frameworks
- **Related Repositories**:
  - Can utilize AI-OS MCP servers as tools for Semantic Kernel
  - Can host AI-OS services as Semantic Kernel skills/plugins
  - Can integrate AI-OS skill system as external capabilities
  - Potentially use AI-OS as underlying platform
- **Advantages**:
  - Brings industry-backed LLM orchestration capabilities
  - Provides familiar SDK experience for enterprise developers
  - Can leverage AI-OS stability and security
  - Enables hybrid approaches with Microsoft ecosystem
- **Limitations**:
  - May introduce licensing or compatibility considerations
  - Integration requires adaptation layer
  - Dependent on external project evolution
- **Future Plans**: Evaluate for hosting Semantic Kernel skills within AI-OS skill system
- **Current Status**: Referenced in documentation as compatible SDK; not currently integrated
- **Historical Note**: Discussed as compatible LLM orchestration approach during architecture evolution

### 5. Memory System

The AI-OS memory system implements a five-tier architecture as originally conceived in the Hermes design. This section distinguishes between internal memory tiers (built into the core implementation) and external memory backends (integrations).

#### Internal Memory Tiers (Core Implementation)
These three tiers are implemented as part of the AI-OS core MemoryManager and are always available:

##### Working Memory
- **Purpose**: Provides short-term, volatile memory for immediate task context and active processing
- **Architectural Role**: First tier of the five-tier memory system, implementing volatile short-term storage
- **Implementation Role**: In-memory data structures with TTL-based eviction, managed by MemoryManager
- **Lifecycle Status**: Active implementation
- **Specification Status**: IMPLEMENTED (Part of Core MemoryManager)
- **Production Readiness**: Development/deployable (Part of v0.1.x)
- **Conformance Requirements**: Must conform to MemoryManager interface in AI-OS Architecture Specification
- **Extension Points**: Eviction policies, storage backends, monitoring hooks
- **Dependencies**:
  - Hermes Kernel interfaces (StateManager, EventBus)
  - Standard Python data structures
- **Related Repositories**:
  - Receives context updates from Planning and Engineering Services
  - Provides immediate context to active agents and services
  - Feeds memory consolidation events to LearningService for transfer to long-term tiers
- **Advantages**:
  - Extremely fast access for active context
  - Automatic cleanup prevents memory leaks
  - Supports working memory patterns for reasoning
- **Limitations**:
  - Volatile nature means data is lost on restart
  - Limited capacity by design
- **Future Plans**: Enhance with adaptive TTL mechanisms, priority-based retention, and monitoring for memory pressure events
- **Current Status**: Implemented in core (`src/aios/memory.py`) - Part of the 5-tier memory system
- **Historical Note**: From original Hermes design as immediate working memory

##### Claude Memory
- **Purpose**: Provides persistent semantic memory for AI-OS learned patterns and user preferences
- **Architectural Role**: Second tier of the five-tier memory system, implementing persistent semantic storage
- **Implementation Role**: Structured storage for agent behaviors, user preferences, and learned patterns
- **Lifecycle Status**: Active implementation
- **Specification Status**: IMPLEMENTED (Part of Core MemoryManager)
- **Production Readiness**: Development/deployable (Part of v0.1.x)
- **Conformance Requirements**: Must conform to MemoryManager interface in AI-OS Architecture Specification
- **Extension Points**: Storage backends, serialization formats, indexing strategies
- **Dependencies**:
  - Hermes Kernel interfaces (StateManager, EventBus)
  - Storage backend (configurable: SQLite, file-based, etc.)
- **Related Repositories**:
  - Receives consolidated memories from Working Memory via LearningService
  - Provides learned patterns to Planning Service for behavior adaptation
  - Stores user preferences and interaction history
- **Advantages**:
  - Persistent across sessions
  - Enables personalized AI behavior
  - Supports learning from interaction history
- **Limitations**:
  - Slower access than Working Memory
  - Requires careful schema evolution management
- **Future Plans**: Enhance with vector embeddings for semantic search, TTL-based pruning, and conflict resolution mechanisms
- **Current Status**: Implemented in core (`src/aios/memory.py`) - Part of the 5-tier memory system
- **Historical Note**: From original Hermes design as persistent semantic memory

##### Engineering Intelligence Memory
- **Purpose**: Provides structured knowledge storage for engineering concepts, code patterns, and technical documentation
- **Architectural Role**: Third tier of the five-tier memory system, implementing structured engineering knowledge storage
- **Implementation Role**: Knowledge vault for code patterns, architectural decisions, technical documentation, and engineering best practices
- **Lifecycle Status**: Active implementation
- **Specification Status**: IMPLEMENTED (Part of Core MemoryManager)
- **Production Readiness**: Development/deployable (Part of v0.1.x)
- **Conformance Requirements**: Must conform to MemoryManager interface in AI-OS Architecture Specification
- **Extension Points**: Knowledge organization schemas, query interfaces, external backend integrations
- **Dependencies**:
  - Hermes Kernel interfaces (StateManager, EventBus)
  - Storage backend (configurable)
  - Optional integration with external knowledge systems (Obsidian, Graphiti/Graphify)
- **Related Repositories**:
  - Receives engineering insights from LearningService and Research Service
  - Provides code patterns and templates to Coding Service
  - Integrates with external knowledge backends for enhanced capabilities
  - Feeds pattern recognition data to LearningService
- **Advantages**:
  - Specialized for engineering knowledge representation
  - Supports code pattern reuse and architectural consistency
  - Enables engineering-specific query capabilities
- **Limitations**:
  - Requires structured input for optimal usefulness
  - May need domain-specific tuning for different engineering fields
- **Current Status**: Implemented in core (`src/aios/memory.py`) - Part of the 5-tier memory system
- **Historical Note**: From original Hermes design as engineering knowledge repository

#### External Memory Backends (Integrations)
These external systems can integrate as enhanced backends for the Engineering Intelligence memory tier:

##### Obsidian
- **Purpose**: Provides popular knowledge vault system for structured documentation and personal knowledge management
- **Architectural Role**: External knowledge vault system that integrates as a memory backend for Engineering Intelligence
- **Implementation Role**: Markdown-based knowledge vault with bidirectional linking, graph views, and knowledge discovery
- **Lifecycle Status**: Specified (not implemented)
- **Specification Status**: SPECIFIED - Memory backend option
- **Production Readiness**: Not applicable (specification only)
- **Conformance Requirements**: Must implement AI-OS MemoryManager MemoryBackend interface
- **Extension Points**: Custom vault formats, synchronization plugins, knowledge discovery algorithms
- **Dependencies**:
  - Obsidian application or compatible markdown-based knowledge system
  - File system access for vault storage
  - AI-OS MemoryManager interface for integration
- **Related Repositories**:
  - Registers as MemoryBackend implementation with MemoryManager
  - Receives knowledge consolidation events from LearningService
  - Provides query interface for retrieving structured knowledge
  - Integrates with Graphify for cross-referencing knowledge entities
- **Advantages**:
  - Leverages popular, well-established knowledge management system
  - Provides rich markdown editing and linking capabilities
  - Enables bidirectional linking and knowledge discovery
  - Supports offline access and synchronization
- **Limitings**:
  - Requires Obsidian installation for full functionality
  - File-based storage may have scaling limitations
  - Dependency on external application ecosystem
- **Future Plans**: Enhance with better synchronization, conflict resolution, and AI-powered knowledge discovery
- **Current Status**: Specified as memory type - Implementation referenced in architecture documents
- **Historical Note**: Part of original five-tier memory system from Hermes-centric architecture

##### Graphiti/Graphify
- **Purpose**: Provides knowledge graph implementation for entity relationships and reasoning
- **Architectural Role**: External knowledge graph system that integrates as a memory backend for Engineering Intelligence
- **Implementation Role**: Graph database for storing and querying entity relationships, dependencies, and knowledge graphs
- **Lifecycle Status**: Specified (not implemented)
- **Specification Status**: SPECIFIED - Memory backend option
- **Production Readiness**: Not applicable (specification only)
- **Conformance Requirements**: Must implement AI-OS MemoryManager MemoryBackend interface
- **Extension Points**: Custom graph schemas, query optimizations, analytics plugins
- **Dependencies**:
  - Graph database technology (Neo4j, JanusGraph, or similar)
  - Graph query language support (Cypher, Gremlin, or similar)
  - AI-OS MemoryManager interface for integration
- **Related Repositories**:
  - Registers as MemoryBackend implementation with MemoryManager
  - Receives entity relationship events from various services
  - Provides graph traversal and query capabilities
  - Integrates with Obsidian for linked document-to-entity relationships
  - Feeds insights to LearningService for pattern extraction
- **Advantages**:
  - Excels at representing complex relationships and dependencies
  - Enables powerful querying and traversal capabilities
  - Supports inference and recommendation systems
  - Scales well with highly connected data
- **Limitations**:
  - More complex to implement and query than simple stores
  - May be overkill for simple key-value storage needs
  - Requires graph database expertise
- **Future Plans**: Enhance with real-time updates, graph algorithms, and AI-powered relationship discovery
- **Current Status**: Specified as memory type - Implementation referenced in architecture documents
- **Historical Note**: Part of original five-tier memory system from Hermes-centric architecture

##### Mem0
- **Purpose**: Provides intelligent memory layer for LLMs with automatic optimization and personalization
- **Architectural Role**: External intelligent memory system that can integrate as enhanced memory backend
- **Implementation Role**: Self-optimizing memory layer for LLMs with automatic organization and retrieval
- **Lifecycle Status**: Specified (not implemented)
- **Specification Status**: SPECIFIED - Potential enhancement
- **Production Readiness**: Not applicable (specification only)
- **Conformance Requirements**: Must implement AI-OS MemoryManager MemoryBackend interface
- **Extension Points**: Custom optimization algorithms, personalization strategies, retrieval methods
- **Dependencies**:
  - Mem0 SDK and API
  - Vector database or storage backend
  - AI-OS MemoryManager interface for integration
- **Related Repositories**:
  - Can register as specialized MemoryBackend with MemoryManager
  - Could enhance Engineering Intelligence memory tier
  - Potentially integrate with LearningService for experience optimization
  - May provide intelligent caching and retrieval
- **Advantages**:
  - Brings intelligent, self-optimizing memory capabilities
  - Automatically organizes and retrieves relevant information
  - Reduces memory management complexity
  - Enhances LLM performance through better context
- **Limitations**:
  - Additional dependency on external service
  - May introduce latency or complexity
  - Requires evaluation of accuracy and relevance
- **Future Plans**: Evaluate for integration as enhanced memory backend; test with specific memory tiers
- **Current Status**: Referenced in documentation as potential integration; not currently implemented
- **Historical Note**: Evaluated during architecture discussions as potential memory enhancement

### 6. MCP Integrations

#### Model Context Protocol (MCP) Infrastructure
- **Purpose**: Provides standardized protocol for connecting AI systems to external tools and data sources
- **Architectural Role**: Core MCPManager capability that provides standardized tool integration framework
- **Implementation Role**: Implements MCP client and server capabilities for standardizing tool access
- **Lifecycle Status**: Active implementation
- **Specification Status**: IMPLEMENTED (Part of Core Managers)
- **Production Readiness**: Development/deployable (Part of v0.1.x)
- **Conformance Requirements**: Must conform to MCPManager Core Manager interface in AI-OS Architecture Specification
- **Extension Points**: Custom transport mechanisms, capability negotiation extensions, resource management
- **Dependencies**:
  - MCP specification implementation
  - Standard tool interfaces and APIs
  - Hermes Kernel interfaces
- **Related Repositories**:
  - Provides standardized interface for external tools
  - Manages MCP server connections and lifecycles
  - Translates between MCP and AI-OS internal interfaces
  - Enables tool discovery, invocation, and result handling
- **Advantages**:
  - Achieves tool independence as required by architectural principles
  - Provides standardized integration framework
  - Enables plug-and-play tool integration
  - Supports secure tool access with capability scoping
- **Limitations**:
  - Requires maintenance of MCP specification compliance
  - May introduce protocol overhead
  - Depends on external MCP server quality
- **Future Plans**: Enhance with advanced capability negotiation and resource management
- **Current Status**: Implemented as Core Manager - Part of the 9 required managers
- **Historical Note**: Evolved from basic ToolManager to full MCPManager implementation

#### Specific MCP Servers
Various MCP servers have been evaluated or implemented for specific tool categories:

##### Filesystem MCP Server
- **Purpose**: Provides standardized file system access through MCP
- **Architectural Role**: External MCP server implementing file system operations
- **Implementation Role**: MCP server exposing file system read/write/search operations
- **Lifecycle Status**: Community-maintained (referenced only)
- **Specification Status**: REFERENCED - Compatible MCP server
- **Production Readiness**: Not applicable (not implemented)
- **Conformance Requirements**: Must implement MCP specification and provide standardized file system operations
- **Extension Points**: Custom file system backends, access control mechanisms, operation optimizations
- **Dependencies**:
  - MCP specification implementation
  - File system access
  - Standard MCP server framework
- **Related Repositories**:
  - Accessed by AI-OS through MCPManager
  - Provides standardized file operations to services
  - Can be replaced by alternative implementations
- **Advantages**:
  - Provides standardized file system interface
  - Enables secure, scoped file access
  - Supports remote and network file systems
  - Compatible with MCP ecosystem
- **Limitations**:
  - Adds dependency on external MCP server
  - May introduce latency vs direct access
  - Requires MCP server maintenance
- **Future Plans**: Evaluate for hosting as official AI-OS MCP server
- **Current Status**: Referenced in documentation as compatible MCP server; community implementations exist
- **Historical Note**: Discussed as standard tool MCP server during architecture evolution

##### Git MCP Server
- **Purpose**: Provides standardized Git version control access through MCP
- **Architectural Role**: External MCP server implementing Git operations
- **Implementation Role**: MCP server exposing Git clone, commit, push, pull, branch operations
- **Lifecycle Status**: Community-maintained (referenced only)
- **Specification Status**: REFERENCED - Compatible MCP server
- **Production Readiness**: Not applicable (not implemented)
- **Conformance Requirements**: Must implement MCP specification and provide standardized Git operations
- **Extension Points**: Custom repository hosting integrations, authentication methods, batch operations
- **Dependencies**:
  - MCP specification implementation
  - Git installation and access
  - Standard MCP server framework
- **Related Repositories**:
  - Accessed by AI-OS through MCPManager
  - Provides standardized Git operations to services
  - Can be replaced by alternative implementations
- **Advantages**:
  - Provides standardized Git interface
  - Enables secure, scoped version control access
  - Supports remote repositories and authentication
  - Compatible with MCP ecosystem
- **Limitations**:
  - Adds dependency on external MCP server
  - May introduce latency vs direct access
  - Requires MCP server maintenance
  - Git complexity requires careful capability scoping
- **Future Plans**: Evaluate for hosting as official AI-OS MCP server
- **Current Status**: Referenced in documentation as compatible MCP server; community implementations exist
- **Historical Note**: Discussed as standard tool MCP server during architecture evolution

##### Search MCP Server
- **Purpose**: Provides standardized search access through MCP (file, code, documentation)
- **Architectural Role**: External MCP server implementing search operations
- **Implementation Role**: MCP server exposing file content, code symbol, and documentation search
- **Lifecycle Status**: Community-maintained (referenced only)
- **Specification Status**: REFERENCED - Compatible MCP server
- **Production Readiness**: Not applicable (not implemented)
- **Conformance Requirements**: Must implement MCP specification and provide standardized search operations
- **Extension Points**: Custom search backends, indexing strategies, query optimization
- **Dependencies**:
  - MCP specification implementation
  - Search engine or indexing capability
  - Standard MCP server framework
- **Related Repositories**:
  - Accessed by AI-OS through MCPManager
  - Provides standardized search operations to services
  - Can be replaced by alternative implementations
- **Advantages**:
  - Provides standardized search interface
  - Enables secure, scoped search access
  - Supports various search backends (ripgrep, Elasticsearch, etc.)
  - Compatible with MCP ecosystem
- **Limitations**:
  - Adds dependency on external MCP server
  - May introduce latency vs direct access
  - Requires MCP server and search backend maintenance
  - Search quality affects results
- **Future Plans**: Evaluate for hosting as official AI-OS MCP server
- **Current Status**: Referenced in documentation as compatible MCP server; community implementations exist
- **Historical Note**: Discussed as standard tool MCP server during architecture evolution

##### Knowledge Graph MCP Server (Graphiti-inspired)
- **Purpose**: Provides standardized knowledge graph access through MCP
- **Architectural Role**: External MCP server implementing knowledge graph operations
- **Implementation Role**: MCP server exposing entity relationship queries, graph traversal, and reasoning
- **Lifecycle Status**: Community-maintained (referenced only)
- **Specification Status**: REFERENCED - Compatible MCP server
- **Production Readiness**: Not applicable (not implemented)
- **Conformance Requirements**: Must implement MCP specification and provide standardized knowledge graph operations
- **Extension Points**: Custom graph databases, query optimizations, traversal algorithms
- **Dependencies**:
  - MCP specification implementation
  - Knowledge graph database (Neo4j, etc.)
  - Graph query language support
  - Standard MCP server framework
- **Related Repositories**:
  - Accessed by AI-OS through MCPManager
  - Provides standardized knowledge graph operations to services
  - Can be replaced by alternative implementations
- **Advantages**:
  - Provides standardized knowledge graph interface
  - Enables secure, scoped knowledge access
  - Supports complex relationship queries and traversal
  - Compatible with MCP ecosystem
- **Limitations**:
  - Adds dependency on external MCP server and knowledge graph
  - May introduce latency vs direct access
  - Requires specialized expertise for maintenance
  - Knowledge graph complexity requires careful design
- **Future Plans**: Evaluate for hosting as official AI-OS MCP server
- **Current Status**: Referenced in documentation as compatible MCP server; referenced in architecture as Graphiti/Graphify integration
- **Historical Note**: Discussed as specialized knowledge MCP server during architecture evolution

#### Vercel Skills
- **Purpose**: Provides standardized skill discovery and distribution mechanism
- **Why Selected**: Referenced in architecture as the official skill discovery mechanism (Vercel Find Skills)
- **Architectural Role**: External skill registry and discovery service referenced in architectural contracts
- **Implementation Role**: Skill discovery service that ranks, versions, and recommends skills for AI-OS consumption
- **Mandatory/Optional**: Referenced as required discovery mechanism in architecture, but implementation can vary
- **Dependencies**:
  - Skill metadata format and schemas
  - HTTP/API access to skill registry
  - SkillManager interface for consumption
- **Interactions**:
  - Used by Capability Discovery Layer in Planning Service
  - Provides discovered skill set to Capability Plan Builder
  - Skills are loaded dynamically via SkillManager
- **Advantages**:
  - Provides standardized skill discovery as required by architecture
  - Enables skill ranking, versioning, and dependency resolution
  - Supports confidence scoring and recommendation
  - Integrates with artifact generation for execution preparation
- **Limitations**:
  - External dependency on skill registry service
  - Requires network access for discovery
  - Skill quality and availability vary
- **Future Plans**: Evaluate for hosting official AI-OS skill registry; enhance with decentralized options
- **Current Status**: Referenced in architecture as required discovery mechanism (Vercel Find Skills)
- **Historical Note**: Explicitly referenced in Part 8 as the capability discovery mechanism

#### Claude Skills
- **Purpose**: Provides skill implementations specifically designed for Claude model ecosystems
- **Why Selected**: Represents skill ecosystem that can integrate with AI-OS skill system
- **Architectural Role**: External skill provider that can register skills with AI-OS SkillManager
- **Implementation Role**: Collection of skills optimized for Claude models and Anthropic ecosystem
- **Mandatory/Optional**: Optional - External skill source that can integrate through standard contracts
- **Dependencies**:
  - Skill interface contracts
  - Claude model access (can route through AI-OS ModelRouter)
  - Standard skill development kit
- **Interactions**:
  - Can register skills with AI-OS SkillManager
  - Skills execute through AI-OS skill execution engine
  - Can consume AI-OS services as dependencies
  - Potentially enhance AI-OS native skill offerings
- **Advantages**:
  - Brings specialized Claude-optimized skill ecosystem
  - Leverages existing Claude skill development investment
  - Can enhance AI-OS capabilities rapidly
  - Maintains compatibility with Claude ecosystem
- **Limitations**:
  - May be overly specific to Claude models
  - Requires evaluation for model independence
  - Depends on external Claude skill ecosystem
- **Future Plans**: Evaluate for integration as skill source; maintain model independence through abstraction
- **Current Status**: Referenced in documentation as compatible skill source; not currently integrated
- **Historical Note**: Discussed during architecture evolution as compatible skill ecosystem

#### Codebase Memory MCP
- **Purpose**: Provides specialized MCP server for codebase understanding and navigation
- **Why Selected**: Represents specialized tool capability for software engineering workflows
- **Architectural Role**: External MCP server implementing codebase analysis and navigation operations
- **Implementation Role**: MCP server exposing code structure, dependencies, documentation, and relationships
- **Mandatory/Optional**: Optional - Enhances tool access for codebase-intensive tasks
- **Dependencies**:
  - MCP specification implementation
  - Codebase analysis and parsing tools
  - Standard MCP server framework
- **Interactions**:
  - Accessed by AI-OS through MCPManager
  - Provides standardized codebase operations to services
  - Can be replaced by alternative implementations
- **Advantages**:
  - Provides standardized codebase interface
  - Enables secure, scoped codebase access
  - Supports dependency analysis, impact assessment, and navigation
  - Compatible with MCP ecosystem
- **Limitations**:
  - Adds dependency on external MCP server
  - May introduce latency vs direct access
  - Requires specialized codebase analysis tools
  - Codebase complexity affects performance and accuracy
- **Future Plans**: Evaluate for hosting as official AI-OS MCP server
- **Current Status**: Referenced in documentation as compatible MCP server; referenced in architecture discussions
- **Historical Note**: Discussed as specialized development MCP server during architecture evolution

### 7. Skills Integrations

#### Standard AI-OS Skills
- **Purpose**: Provide reusable capabilities for AI-OS services and agents
- **Why Selected**: Embodies architectural principle of skills as first-class architectural components
- **Architectural Role**: Internal skill system implementing the SkillManager Core Manager
- **Implementation Role**: Contains built-in skills for common engineering operations (code generation, review, testing, etc.)
- **Mandatory/Optional**: Mandatory - SkillManager is one of the 9 required Core Managers
- **Dependencies**:
  - Skill interface contracts and schemas
  - Sandboxed execution environment
  - Standard skill development kit
- **Interactions**:
  - Loaded and executed via SkillManager
  - Discovered through Capability Discovery Layer (Vercel Find Skills)
  - Integrated into capability plans by Planning Service
  - Executed by Engineering Services as needed
- **Advantages**:
  - Provides reusable, versioned capabilities
  - Enables skill composition and chaining
  - Supports dynamic loading and unloading
  - Includes sandboxed execution for security
- **Limitations**:
  - Requires skill development and maintenance
  - Sandboxing may introduce performance overhead
  - Skill quality affects service reliability
- **Future Plans**: Enhance with skill marketplace, versioning, and enterprise governance
- **Current Status**: Implemented as Core Manager - Part of the 9 required managers; skills being developed
- **Historical Note**: Evolved from basic skill system to first-class architectural component

### 8. Development Tools

#### RuFF
- **Purpose**: Provides fast Python code formatting and linting
- **Why Selected**: Chosen as primary code quality tool for AI-OS development
- **Architectural Role**: External development tool used in AI-OS codebase maintenance
- **Implementation Role**: Fast Python linter and formatter written in Rust
- **Mandatory/Optional**: Optional - Development tool, not required for runtime
- **Dependencies**:
  - Python environment
  - Standard command-line interface
- **Interactions**:
  - Used in development workflow for code quality
  - Integrated into pre-commit hooks and CI pipelines
  - Configured via project settings
- **Advantages**:
  - Extremely fast performance (written in Rust)
  - Combines linting and formatting capabilities
  - Active development and maintenance
  - Zero configuration defaults
- **Limitations**:
  - May not catch all issues that specialized linters find
  - Less configurable than some alternatives
  - Dependency on external tool maintenance
- **Future Plans**: Continue as primary code quality tool; evaluate for enhanced rule sets
- **Current Status**: Used in development - configured in pyproject.toml and CI
- **Historical Note**: Selected during early development as part of modern Python toolchain

#### mypy
- **Purpose**: Provides static type checking for Python code
- **Why Selected**: Selected for ensuring type safety in AI-OS Python codebase
- **Architectural Role**: External development tool used in AI-OS codebase maintenance
- **Implementation Role**: Static type checker for Python
- **Mandatory/Optional**: Optional - Development tool, not required for runtime
- **Dependencies**:
  - Python environment
  - Type annotations in codebase
  - Standard command-line interface
- **Interactions**:
  - Used in development workflow for type safety
  - Integrated into pre-commit hooks and CI pipelines
  - Configured via project settings (mypy.ini)
- **Advantages**:
  - Industry standard for Python type checking
  - Catches type errors before runtime
  - Gradual typing support
  - Well-integrated with Python ecosystem
- **Limitations**:
  - Can produce false positives
  - Requires diligent type annotation maintenance
  - Can slow down development workflow
- **Future Plans**: Continue as primary type checking tool; enhance coverage over time
- **Current Status**: Used in development - configured in mypy.ini and CI
- **Historical Note**: Selected during early development as part of modern Python toolchain

#### pytest
- **Purpose**: Provides testing framework for Python code
- **Why Selected**: Selected as primary testing framework for AI-OS
- **Architectural Role**: External development tool used in AI-OS codebase maintenance
- **Implementation Role**: Testing framework for Python
- **Mandatory/Optional**: Optional - Development tool, not required for runtime
- **Dependencies**:
  - Python environment
  - Standard command-line interface
  - Test discovery and collection mechanisms
- **Interactions**:
  - Used in development workflow for testing
  - Integrated into pre-commit hooks and CI pipelines
  - Configured via project settings (pytest.ini)
- **Advantages**:
  - Industry standard for Python testing
  - Rich plugin ecosystem
  - Excellent discovery and reporting capabilities
  - Well-integrated with Python ecosystem
- **Limitations**:
  - Can be slow for large test suites
  - Requires disciplined test writing and maintenance
  - Test isolation can be challenging
- **Future Plans**: Continue as primary testing tool; enhance with property-based testing and benchmarking
- **Current Status**: Used in development - configured in pytest.ini and CI
- **Historical Note**: Selected during early development as part of modern Python toolchain

### 9. Evaluation Tools

#### Promptfoo
- **Purpose**: Provides framework for evaluating LLM prompts and outputs
- **Why Selected**: Represents modern approach to prompt engineering evaluation that can validate AI-OS LLM interactions
- **Architectural Role**: External prompt evaluation framework
- **Implementation Role**: Framework for testing and evaluating LLM prompts with structured testing
- **Mandatory/Optional**: Optional - Evaluation and testing tool
- **Dependencies**:
  - LLM API access (can route through AI-OS ModelRouter)
  - Standard prompt and response formats
  - Evaluation metric definitions
- **Interactions**:
  - Can evaluate AI-OS LLM interactions and prompts
  - Can test ModelRouter capability-based routing
  - Potentially integrate as specialized evaluation service within AI-OS
- **Advantages**:
  - Brings structured prompt engineering evaluation
  - Enables reproducible LLM testing
  - Supports automated regression testing
  - Provides detailed failure analysis
- **Limitations**:
  - Evaluation-focused; may not represent production usage
  - Requires definition of quality metrics
  - Dependent on external project maintenance
- **Future Plans**: Host official Promptfoo evaluation for AI-OS prompts; use for continuous improvement
- **Current Status**: Referenced in documentation as evaluation framework; not currently integrated
- **Historical Note**: Discussed as potential validation mechanism for LLM interactions

#### DeepEval
- **Purpose**: Provides comprehensive LLM evaluation framework with metrics and benchmarking
- **Why Selected**: Represents thorough approach to LLM system evaluation that can validate AI-OS LLM capabilities
- **Architectural Role**: External LLM evaluation framework
- **Implementation Role**: Framework for evaluating LLMs and LLM systems with standardized metrics
- **Mandatory/Optional**: Optional - Evaluation and testing tool
- **Dependencies**:
  - LLM API access (can route through AI-OS ModelRouter)
  - Standard evaluation formats and metrics
  - Benchmark dataset definitions
- **Interactions**:
  - Can evaluate AI-OS LLM capabilities and services
  - Can test end-to-end LLM interactions through AI-OS
  - Potentially integrate as specialized evaluation service within AI-OS
- **Advantages**:
  - Brings comprehensive LLM evaluation capabilities
  - Provides standardized metrics and benchmarking
  - Enables comparison against industry baselines
  - Supports continuous improvement through measurement
- **Limitations**:
  - Comprehensive evaluation can be resource-intensive
  - Requires definition of relevant metrics for use case
  - Dependent on external project maintenance
- **Future Plans**: Host official DeepEval evaluation for AI-OS LLM capabilities; use for validation and improvement
- **Current Status**: Referenced in documentation as evaluation framework; not currently integrated
- **Historical Note**: Discussed as potential validation mechanism for LLM capabilities

## Reference Architecture Diagram

```mermaid
graph TD
    %% Core Layers - Architecture & Runtime
    A[AI-OS Architecture Specification<br/>FROZEN - Source of Truth] --> B[ai-os Reference Implementation<br/>Hermes Runtime]
    
    %% Core Managers (9) - Part of Core Implementation
    B --> C1[EventBus<br/>Core Component]
    B --> C2[StateManager<br/>Core Component]
    B --> C3[WorkflowManager<br/>Core Component]
    B --> C4[ResourceManager<br/>Core Component]
    B --> C5[MemoryManager<br/>Core Manager]
    B --> C6[ModelRouter<br/>Core Manager]
    B --> C7[MCPManager<br/>Core Manager]
    B --> C8[SkillManager<br/>Core Manager]
    B --> C9[CouncilManager<br/>Core Manager]
    B --> C10[AI Agency Service<br/>Core Manager]
    B --> C11[ObservabilityManager<br/>Core Manager]
    
    %% Engineering Services (Core Implementation)
    C5 --> D1[Planning Service<br/>Engineering Service]
    D1 --> D2[Coding Service<br/>Engineering Service]
    D2 --> D3[Review Service<br/>Engineering Service]
    D3 --> D4[Testing Service<br/>Engineering Service]
    D4 --> D5[Deployment Service<br/>Engineering Service]
    D5 --> D6[Operations Service<br/>Engineering Service]
    D6 --> D7[Learning Service<br/>Engineering Service]
    D7 --> D8[Memory Service<br/>Engineering Service]
    
    %% Facade Services (Core Implementation)
    C8 --> E1[SkillService<br/>Facade Service]
    C9 --> E2[CouncilService<br/>Facade Service]
    C7 --> E3[MCPService<br/>Facade Service]
    C5 --> E4[MemoryService<br/>Facade Service]
    
    %% Extensions - External Integrations
    E1 --> F1[Skills<br/>External Integration]
    C5 --> F2[Memory Backends<br/>External Integration]
    C7 --> F3[MCP Transports/Servers<br/>External Integration]
    C10 --> F4[AI Agents<br/>External Integration]
    C6 --> F5[Model Providers<br/>External Integration]
    C9 --> F6[Consensus Algorithms<br/>External Integration]
    
    %% Specific Integrations by Category
    %% Memory Integrations
    F2 --> G1[Obsidian<br/>Memory Integration]
    F2 --> G2[Graphiti/Graphify<br/>Memory Integration]
    F2 --> G3[Mem0<br/>Memory Integration]
    
    %% MCP Integrations
    F3 --> G4[Filesystem MCP<br/>MCP Integration]
    F3 --> G5[Git MCP<br/>MCP Integration]
    F3 --> G6[Search MCP<br/>MCP Integration]
    F3 --> G7[Knowledge Graph MCP<br/>MCP Integration]
    
    %% Skills Integrations
    F1 --> G8[Vercel Skills<br/>Skills Integration]
    F1 --> G9[Claude Skills<br/>Skills Integration]
    
    %% External Integrations
    B --> H1[free-claude-code<br/>External Integration]
    B --> H2[OpenHands<br/>External Integration]
    B --> H3[Continue<br/>External Integration]
    B --> H4[Cline<br/>External Integration]
    B --> H5[Aider<br/>External Integration]
    
    %% Evaluation Tools
    B --> H6[SWE-Agent<br/>Evaluation Tool]
    F1 --> G10[Promptfoo<br/>Evaluation Tool]
    F1 --> G11[DeepEval<br/>Evaluation Tool]
    B --> H7[AutoGen<br/>External Integration]
    B --> H8[CrewAI<br/>External Integration]
    B --> H9[LangGraph<br/>External Integration]
    B --> H10[Semantic Kernel<br/>External Integration]
    
    %% Styling
    classDef core fill:#f9f,stroke:#333,stroke-width:2px;
    classDef manager fill:#bbf,stroke:#333,stroke-width:1px;
    classDef service fill:#bfb,stroke:#333,stroke-width:1px;
    classDef facade fill:#ffb,stroke:#333,stroke-width:1px;
    classDef extension fill:#fbb,stroke:#333,stroke-width:1px;
    classDef integration fill:#bfb,stroke:#333,stroke-width:1px;
    classDef eval fill:#ff9,stroke:#333,stroke-width:1px;
    classDef dev fill:#9f9,stroke:#333,stroke-width:1px;
    classDef agency fill:#f99,stroke:#333,stroke-width:1px;
    
    class A,B core;
    class C1,C2,C3,C4,C5,C6,C7,C8,C9,C11 manager;
    class C10 agency;
    class D1,D2,D3,D4,D5,D6,D7,D8 service;
    class E1,E2,E3,E4 facade;
    class F1,F2,F3,F4,F5,F6 extension;
    class G1,G2,G3 integration;
    class G4,G5,G6,G7 integration;
    class G8,G9 integration;
    class H1,H2,H3,H4,H5 integration;
    class H6,H7,H8,H9,H10,G10,G11 eval;
    class %% Dev tools not shown in this architectural view
```

## Summary Statistics

### By Classification Type:
- **Core Architecture Repository**: 1 (AI-OS Architecture Specification - Parts 1-15)
- **Core Implementation Repository**: 1 (ai-os/Hermes Runtime)
- **AI Agency**: 1 (AI Agency Service)
- **Reference Implementations**: 2 (ObservabilityManager, ModelRouter)
- **External Integrations**: 10 (free-claude-code, OpenHands, Continue, Cline, Aider, SWE-Agent, AutoGen, CrewAI, LangGraph, Semantic Kernel)
- **Memory Integrations**: 7 (Internal: Working Memory, Claude Memory, Engineering Intelligence Memory; External: Obsidian, Graphiti/Graphify, Mem0, plus potential enhancements)
- **MCP Integrations**: 5 (MCP Manager Core + 4 specific servers: Filesystem, Git, Search, Knowledge Graph)
- **Skills Integrations**: 3 (Standard AI-OS Skills, Vercel Skills discovery service, Claude Skills source)
- **Development Tools**: 3 (RuFF, mypy, pytest)
- **Evaluation Tools**: 3 (Promptfoo, DeepEval, SWE-Agent)
- **Total Catalogued Repositories**: 32+ distinct repository types

### Status Distribution:
- **FROZEN/Authoritative**: 1 item (AI-OS Architecture Specification)
- **IMPLEMENTED (v0.1.x)**: 5 items (Core implementation + 4 Reference Managers: AI Agency, ObservabilityManager, ModelRouter, MCPManager)
- **SPECIFIED/PLANNED**: 12 items (Memory backend options, MCP server options, skill discovery services)
- **REFERENCED/COMPATIBLE**: 15 items (External frameworks, tools, and SDKs referenced for potential integration)
- **EVALUATION FRAMEWORKS**: 3 items (Promptfoo, DeepEval, SWE-Agent)
- **DEVELOPMENT TOOLS**: 3 items (RuFF, mypy, pytest)

## Historical Preservation Notes

This document preserves key historical decisions from the AI-OS architecture evolution:

1. **Original Hermes-Centric Concepts**: The five-tier memory system (Working, Claude, Engineering, Obsidian, Graphify) originates from the original Hermes design
2. **Governance Evolution**: From simple Claude Council voting to pluggable consensus algorithms with FinalJudge gateway
3. **Tool Integration Evolution**: From basic ToolManager to full MCPManager implementation with standardized discovery
4. **Skill System Evolution**: From simple function execution to first-class architectural components with discovery contracts
5. **LLM Routing Evolution**: From basic LLMManager to capability-based ModelRouter with provider abstraction
6. **Observability Evolution**: From basic logging to OpenTelemetry-compatible distributed tracing and metrics

All historical architectural decisions are preserved where they continue to inform the current specification, with clear indications of which elements are active, legacy, reference-only, or planned for future implementation.

*Document Version: 2.0.0*
*Last Updated: 2026-08-06*
*Status: COMPLETE - Definitive Repository Ecosystem Specification*