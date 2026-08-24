| File | Changed? | M3-related? | Correct? | Risk |
|---|---|---|---|---|
| pyproject.toml | Yes | Indirect (test infrastructure) | Yes - Added testpaths for clean test collection | Low |
| src/aios/__init__.py | Yes | Indirect (API exports) | Yes - Expanded __all__ for proper API completion | Low |
| src/aios/core/checkpoint.py | Yes | Yes - Event emission fix | Partially - Moved _emit_event method and fixed UUID parsing | Medium |
| src/aios/core/council_manager.py | Yes | Yes - Event handling | Yes - Made methods async and fixed event emission | Low |
| src/aios/core/kernel.py | Yes | Yes - EventBus config | Yes - Added event_bus_max_dispatch_depth config | Low |
| src/aios/core/mcp_manager.py | Yes | Yes - Event handling | Yes - Fixed UUID handling and event types | Low |
| src/aios/core/memory.py | Yes | Yes - Event handling | Yes - Fixed UUID handling | Low |
| src/aios/core/retry.py | Yes | Yes - Event handling | Yes - Made methods async | Low |
| src/aios/core/root_cause.py | Yes | Yes - Core M3 component | Partially - Added shutdown() and improved lifecycle management | Medium |
| src/aios/core/workflow.py | Yes | Yes - Execution component | Yes - Minor improvements | Low |
| src/aios/events/core/event.py | Yes | Yes - Event infrastructure | Yes - Minor improvements | Low |
| src/aios/events/types.py | Yes | Yes - Canonical EventType | Yes - Updated enum | Low |
| src/aios/services/base.py | Yes | Yes - Service base | Yes - Improved base service functionality | Low |
| src/aios/services/council.py | Yes | Yes - Council service | Yes - Improved council implementations | Low |
| src/aios/services/learning.py | Yes | Yes - Learning service | Yes - Improved learning functionality | Low |
| src/aios/services/memory.py | Yes | Yes - Memory service | Yes - Improved memory functionality | Low |
| src/aios/services/planning.py | Yes | Yes - Planning service | Yes - Improved planning functionality | Low |
| src/aios/services/skill.py | Yes | Yes - Skill service | Yes - Improved skill functionality | Low |
| tests/integration/test_integration.py | Yes | Yes - Integration tests | Yes - Fixed test issues | Low |
| tests/test_cli.py | Deleted | No - Cleanup | Yes - Removed empty stub | Low |
| tests/test_config.py | Deleted | No - Cleanup | Yes - Removed empty stub | Low |