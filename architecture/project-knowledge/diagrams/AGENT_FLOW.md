```mermaid
flowchart TD
    %% Main Flow
    A[Start] --> B[Goal Formation]
    B --> C[Planner]
    C --> D[Council Interaction]
    D --> E[Task Decomposition]
    E --> F{Human Approval?}
    F -->|Yes| G[Delegation]
    F -->|No| C
    
    %% Single-Agent Execution Path
    G --> SA[Single-Agent Execution]
    subgraph SA_Flow["Single-Agent Execution"]
        direction TB
        SA1[Capability Resolver] --> SA2[Skill Selection]
        SA2 --> SA3[MCP Selection]
        SA3 --> SA4[Agent Manager\n(Lifecycle & States)]
        SA4 --> EE_SA[Execution Engine\n(Checkpointing/Recovery/Retry)]
        EE_SA --> SA5[Agent Output]
        SA5 --> SA_Out
    end
    
    %% Multi-Agent Orchestration Path
    G --> MA[Multi-Agent Orchestration]
    subgraph MA_Flow["Multi-Agent Orchestration"]
        direction TB
        MA1[Workflow Manager] --> MA2[Sub-Agent Creation]
        MA2 --> MA3[Parallel Agents]
        MA3 --> MA4[Dependency Graph]
        MA4 --> MA5[Agent Communication\n(Inter-Agent Messaging)]
        MA5 --> MA6[Agent Hierarchy]
        MA6 --> MA7[Distribute Tasks]
        MA7 --> MA8[Agent Execution (xN)]
        subgraph MA_Agent["Each Agent Execution"]
            direction TB
            MA8A[Capability Resolver] --> MA8B[Skill Selection]
            MA8B --> MA8C[MCP Selection]
            MA8C --> MA8D[Agent Manager\n(Lifecycle & States)]
            MA8D --> EE_MA[Execution Engine\n(Checkpointing/Recovery/Retry)]
            EE_MA --> MA8E[Agent Output]
        end
        MA8 --> MA_Agent
        MA_Agent --> MA9[Results Collection]
        MA9 --> MA_Out
    end
    
    %% Convergence Point
    SA_Out --> V[Validation]
    MA_Out --> V
    
    %% Validation & Judgment
    V --> FJ[Final Judge]
    FJ -->|Approved| R[Reflection]
    FJ -->|Not Approved| RP[Replanning]
    RP --> C
    
    %% Learning & Memory
    R --> L[Learning]
    L --> MI[Memory Interaction]
    MI --> CF[Capability Feedback]
    CF --> SA1
    CF --> MA8A
    
    %% Completion & Termination
    R --> Comp[Completion]
    Comp --> Term[Termination]
    
    %% Styling
    classDef mainFlow fill:#E3F2FD,stroke:#1565C0,stroke-width:2px;
    classDef decision fill:#FFF3E0,stroke:#EF6C00,stroke-width:2px;
    classDef subFlow fill:#E8F5E8,stroke:#2E7D32,stroke-width:2px;
    classDef validation fill:#FFEBEE,stroke:#C62828,stroke-width:2px;
    classDef learning fill:#F3E5F5,stroke:#6A1B9A,stroke-width:2px;
    classDef termination fill:#E8F5E9,stroke:#1B5E20,stroke-width:2px;
    class A,B,C,D,E,F,G mainFlow
    class F decision
    class SA_Flow,MA_Flow subFlow
    class V,FJ,RP validation
    class L,MI,CF learning
    class Comp,Term termination
    class EE_SA,EE_MA subFlow