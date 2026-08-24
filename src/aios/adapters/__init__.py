"""AI-OS adapters package.

External-execution adapters for the multi-perspective testing system (M7).
Each adapter performs REAL execution behind an injection seam; the production
execution path talks to real tools (static analyzers, benchmark harnesses,
fault injectors, MCP servers) while tests inject deterministic doubles.

No adapter invents a verdict itself; it returns structured observations that
``TestOrchestratorService.normalize_evidence`` converts into ``TestingEvidence``.
"""
