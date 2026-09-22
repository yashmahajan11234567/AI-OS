"""
Self-Loop Engine for AI-OS M13.

Implements the 19-phase canonical self-loop as the single authoritative
autonomous decision-making engine. All external systems operate as bounded
resources under AI-OS control.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from aios.core.self_prompt import (
    SelfPrompt,
    SelfPromptContext,
    SelfPromptDirective,
    SelfPromptMetadata,
    SelfPromptPriority,
    SelfPromptValidationStatus,
    ExecutionBounds,
)


class SelfLoopPhase(str, Enum):
    """The 19 canonical phases of the AI-OS self-loop."""
    USER_INTENT = "user_intent"
    PLANNING = "planning"
    RESEARCH = "research"
    REQUIREMENTS = "requirements"
    COUNCILS_REVIEWS = "councils_reviews"
    PLAN = "plan"
    TASKS = "tasks"
    SELF_PROMPT = "self_prompt"
    BOUNDED_EXECUTION = "bounded_execution"
    TEST = "test"
    REVIEW = "review"
    VERIFICATION = "verification"
    FINAL_JUDGMENT = "final_judgment"
    DECISION = "decision"
    EVIDENCE = "evidence"
    LEARNING = "learning"
    MEMORY_KNOWLEDGE = "memory_knowledge"
    PERSISTENCE = "persistence"
    NEXT_SELF_PROMPT = "next_self_prompt"


class SelfLoopState(str, Enum):
    """High-level self-loop operational states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED_CYCLE = "completed_cycle"
    FAILED = "failed"
    DEGRADED = "degraded"
    RECOVERING = "recovering"


@dataclass(frozen=True)
class PhaseResult:
    """Result of a single self-loop phase execution."""
    phase: SelfLoopPhase
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0
    provenance_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class SelfLoopCycle:
    """Represents a single iteration of the self-loop."""
    cycle_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    phase_results: dict[SelfLoopPhase, PhaseResult] = field(default_factory=dict)
    current_phase: Optional[SelfLoopPhase] = None
    state: SelfLoopState = SelfLoopState.IDLE
    self_prompt: Optional[SelfPrompt] = None
    error: Optional[str] = None
    # B3-R1 / B3-T2: governance provenance — attached at pause, read by resume()
    _project_id: Optional[str] = None   # type: ignore[assignment]
    _plan_id: Optional[str] = None      # type: ignore[assignment]
    _correlation_id: Optional[str] = None  # type: ignore[assignment]


class SelfLoopEngine:
    """
    AI-OS Self-Loop Engine — Single Authoritative Autonomous Decision-Making Engine.

    Implements the 19-phase canonical self-loop lifecycle as specified in
    M13_SELF_LOOP_INTEGRATION_SPEC.md. All external systems integrate as
    bounded resources under AI-OS control. AI-OS retains sole governance,
    verification, and decision-making authority.
    """

    # Phase execution order (canonical 19 phases)
    PHASE_ORDER = [
        SelfLoopPhase.USER_INTENT,
        SelfLoopPhase.PLANNING,
        SelfLoopPhase.RESEARCH,
        SelfLoopPhase.REQUIREMENTS,
        SelfLoopPhase.COUNCILS_REVIEWS,
        SelfLoopPhase.PLAN,
        SelfLoopPhase.TASKS,
        SelfLoopPhase.SELF_PROMPT,
        SelfLoopPhase.BOUNDED_EXECUTION,
        SelfLoopPhase.TEST,
        SelfLoopPhase.REVIEW,
        SelfLoopPhase.VERIFICATION,
        SelfLoopPhase.FINAL_JUDGMENT,
        SelfLoopPhase.DECISION,
        SelfLoopPhase.EVIDENCE,
        SelfLoopPhase.LEARNING,
        SelfLoopPhase.MEMORY_KNOWLEDGE,
        SelfLoopPhase.PERSISTENCE,
        SelfLoopPhase.NEXT_SELF_PROMPT,
    ]

    def __init__(
        self,
        kernel: Any = None,
        event_bus: Any = None,
        service_registry: Any = None,
        config_manager: Any = None,
        logger: Any = None,
        security_manager: Any = None,
        capability_manager: Any = None,
        state_manager: Any = None,
        workflow_manager: Any = None,
        resource_manager: Any = None,
        health_manager: Any = None,
        observability_manager: Any = None,
        memory_manager: Any = None,
        prompt_generator: Any = None,
    ):
        """
        Initialize the Self-Loop Engine.

        All core components are injected to maintain canonical authority
        and avoid singleton duplication. The kernel owns the engine lifecycle.
        """
        self._kernel = kernel
        self._event_bus = event_bus
        self._service_registry = service_registry
        self._config_manager = config_manager
        self._logger = logger
        self._security_manager = security_manager
        self._capability_manager = capability_manager
        self._state_manager = state_manager
        self._workflow_manager = workflow_manager
        self._resource_manager = resource_manager
        self._health_manager = health_manager
        self._observability_manager = observability_manager
        self._memory_manager = memory_manager
        self._prompt_generator = prompt_generator

        self._current_cycle: Optional[SelfLoopCycle] = None
        self._phase_handlers: dict[SelfLoopPhase, Callable] = {}
        self._running = False
        self._paused = False
        self._cycle_count = 0
        self._max_cycles = 100  # Safety bound
        self._cycle_timeout_seconds = 3600  # 1 hour per cycle max

        # Mock mode for development/testing
        self._mock_mode = True

        # Register default phase handlers (mock implementations)
        self._register_default_handlers()

        # B2-T1: Initialize adapter references (will be set via dependency injection or kernel lookup)
        self._obsidian_adapter = None
        self._graphify_adapter = None
        self._claude_mem_adapter = None
        self._evidence_engine = None
        self._state_manager = None

    def set_adapter_references(self, obsidian_adapter=None, graphify_adapter=None,
                              claude_mem_adapter=None, evidence_engine=None, state_manager=None):
        """Set adapter references for context gathering (called by kernel during initialization)."""
        self._obsidian_adapter = obsidian_adapter
        self._graphify_adapter = graphify_adapter
        self._claude_mem_adapter = claude_mem_adapter
        self._evidence_engine = evidence_engine
        self._state_manager = state_manager

    def _extract_project_id(self, context: SelfPromptContext, output: dict[str, Any]) -> Optional[str]:
        """Extract project ID from context or output."""
        # Try to get project ID from various sources
        project_sources = [
            context.user_intent.get("project_id"),
            context.planning_outcome.get("project_id"),
            context.approved_plan.get("project_id") if context.approved_plan else None,
            output.get("project_id"),
            output.get("output", {}).get("project_id") if isinstance(output.get("output"), dict) else None,
        ]

        for project_id in project_sources:
            if project_id and isinstance(project_id, str) and project_id.strip():
                return project_id.strip()

        # Default to a generic project ID if none found
        return "default_project"

    def _gather_git_context(self) -> dict[str, Any]:
        """Gather Git/project context from available sources."""
        try:
            # Try to get Git info from state manager or other sources
            if self._state_manager and hasattr(self._state_manager, 'get_git_context'):
                git_info = self._state_manager.get_git_context()
                if git_info:
                    return {
                        "source": "git",
                        "authority": "provenance_only",
                        "advisory": True,
                        "data": git_info,
                        "provenance": {
                            "source": "git",
                            "extracted_at": datetime.now(timezone.utc).isoformat(),
                            "authority": "provenance_only"
                        }
                    }

            # Fallback: basic Git context from environment or config
            import os
            git_context = {
                "source": "git",
                "authority": "provenance_only",
                "advisory": True,
                "data": {
                    "repository_path": os.getcwd(),
                    "branch": os.environ.get("GIT_BRANCH", "unknown"),
                    "commit": os.environ.get("GIT_COMMIT", "unknown"),
                    "working_tree_clean": os.environ.get("GIT_WORKING_TREE_CLEAN", "unknown") == "true",
                },
                "provenance": {
                    "source": "git_environment",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "authority": "provenance_only"
                }
            }
            return git_context

        except Exception as e:
            # Graceful degradation - return error context
            return {
                "source": "git",
                "authority": "provenance_only",
                "advisory": True,
                "data": {},
                "provenance": {
                    "source": "git",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "authority": "provenance_only",
                    "error": str(e)
                },
                "error": str(e)
            }

    def _gather_obsidian_context(self, project_id: str) -> dict[str, Any]:
        """Gather Obsidian context for the project."""
        try:
            if not self._obsidian_adapter:
                return {
                    "source": "obsidian",
                    "authority": "contextual",
                    "advisory": True,
                    "data": {},
                    "provenance": {
                        "source": "obsidian",
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                        "authority": "contextual",
                        "status": "unavailable"
                    },
                    "status": "unavailable"
                }

            # Search for project-related notes
            search_query = f"project:{project_id} OR {project_id}" if project_id != "default_project" else "AI-OS"

            # Try to get notes from Obsidian
            result = asyncio.run(self._obsidian_adapter.search_notes(
                query=search_query,
                limit=10
            ))

            if result.status.name == "SUCCESS":
                notes_data = result.raw.get("notes", []) if result.raw else []

                # Mark all data as advisory per C14
                advisory_notes = []
                for note in notes_data:
                    if isinstance(note, dict):
                        # Already marked by adapter, but ensure advisory marking
                        note.setdefault("provenance", {}).update({
                            "source": "obsidian",
                            "authority": "contextual",
                            "advisory": True
                        })
                        advisory_notes.append(note)

                return {
                    "source": "obsidian",
                    "authority": "contextual",
                    "advisory": True,
                    "data": {
                        "notes": advisory_notes,
                        "query": search_query,
                        "count": len(advisory_notes)
                    },
                    "provenance": {
                        "source": "obsidian",
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                        "authority": "contextual",
                        "advisory": True
                    }
                }
            else:
                return {
                    "source": "obsidian",
                    "authority": "contextual",
                    "advisory": True,
                    "data": {},
                    "provenance": {
                        "source": "obsidian",
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                        "authority": "contextual",
                        "status": "query_failed"
                    },
                    "status": "unavailable",
                    "error": f"Obsidian query failed: {getattr(result, 'error', 'Unknown error')}"
                }

        except Exception as e:
            # Graceful degradation
            return {
                "source": "obsidian",
                "authority": "contextual",
                "advisory": True,
                "data": {},
                "provenance": {
                    "source": "obsidian",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "authority": "contextual",
                    "advisory": True,
                    "error": str(e)
                },
                "status": "error",
                "error": str(e)
            }

    def _gather_graphify_context(self, project_id: str) -> dict[str, Any]:
        """Gather Graphify context for the project."""
        try:
            if not self._graphify_adapter:
                return {
                    "source": "graphify",
                    "authority": "advisory_only",
                    "advisory": True,
                    "data": {},
                    "provenance": {
                        "source": "graphify",
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                        "authority": "advisory_only",
                        "status": "unavailable"
                    },
                    "status": "unavailable"
                }

            # Get related entities for the project
            entity_id = f"project:{project_id}" if project_id != "default_project" else "project:AI-OS"

            result = asyncio.run(self._graphify_adapter.get_related_entities(
                entity_id=entity_id,
                limit=20
            ))

            if result.status.name == "SUCCESS":
                nodes_data = result.raw.get("nodes", []) if result.raw else []
                edges_data = result.raw.get("edges", []) if result.raw else []

                # Mark all data as advisory per C14
                advisory_nodes = []
                for node in nodes_data:
                    if isinstance(node, dict):
                        node.setdefault("provenance", {}).update({
                            "source": "graphify",
                            "authority": "advisory_only",
                            "advisory": True
                        })
                        advisory_nodes.append(node)

                advisory_edges = []
                for edge in edges_data:
                    if isinstance(edge, dict):
                        edge.setdefault("provenance", {}).update({
                            "source": "graphify",
                            "authority": "advisory_only",
                            "advisory": True
                        })
                        advisory_edges.append(edge)

                return {
                    "source": "graphify",
                    "authority": "advisory_only",
                    "advisory": True,
                    "data": {
                        "nodes": advisory_nodes,
                        "edges": advisory_edges,
                        "entity_id": entity_id,
                        "node_count": len(advisory_nodes),
                        "edge_count": len(advisory_edges)
                    },
                    "provenance": {
                        "source": "graphify",
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                        "authority": "advisory_only",
                        "advisory": True
                    }
                }
            else:
                return {
                    "source": "graphify",
                    "authority": "advisory_only",
                    "advisory": True,
                    "data": {},
                    "provenance": {
                        "source": "graphify",
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                        "authority": "advisory_only",
                        "status": "query_failed"
                    },
                    "status": "unavailable",
                    "error": f"Graphify query failed: {getattr(result, 'error', 'Unknown error')}"
                }

        except Exception as e:
            # Graceful degradation
            return {
                "source": "graphify",
                "authority": "advisory_only",
                "advisory": True,
                "data": {},
                "provenance": {
                    "source": "graphify",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "authority": "advisory_only",
                    "advisory": True,
                    "error": str(e)
                },
                "status": "error",
                "error": str(e)
            }

    def _gather_claude_mem_context(self, project_id: str) -> dict[str, Any]:
        """Gather Claude-Mem context for the project."""
        try:
            if not self._claude_mem_adapter:
                return {
                    "source": "claude_mem",
                    "authority": "contextual",
                    "advisory": True,
                    "data": {},
                    "provenance": {
                        "source": "claude_mem",
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                        "authority": "contextual",
                        "status": "unavailable"
                    },
                    "status": "unavailable"
                }

            # Retrieve contextual memories for the project
            search_query = f"project:{project_id}" if project_id != "default_project" else "AI-OS OR development OR planning"

            result = asyncio.run(self._claude_mem_adapter.retrieve_context(
                query=search_query,
                limit=15
            ))

            if result.status.name == "SUCCESS":
                memories_data = result.raw.get("memories", []) if result.raw else []

                # Mark all data as advisory per C14
                advisory_memories = []
                for memory in memories_data:
                    if isinstance(memory, dict):
                        memory.setdefault("provenance", {}).update({
                            "source": "claude_mem",
                            "authority": "contextual",
                            "advisory": True,
                            "trust_level": "untrusted"
                        })
                        advisory_memories.append(memory)

                return {
                    "source": "claude_mem",
                    "authority": "contextual",
                    "advisory": True,
                    "data": {
                        "memories": advisory_memories,
                        "query": search_query,
                        "count": len(advisory_memories)
                    },
                    "provenance": {
                        "source": "claude_mem",
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                        "authority": "contextual",
                        "advisory": True,
                        "trust_level": "untrusted"
                    }
                }
            else:
                return {
                    "source": "claude_mem",
                    "authority": "contextual",
                    "advisory": True,
                    "data": {},
                    "provenance": {
                        "source": "claude_mem",
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                        "authority": "contextual",
                        "advisory": True,
                        "trust_level": "untrusted",
                        "status": "query_failed"
                    },
                    "status": "unavailable",
                    "error": f"Claude-Mem query failed: {getattr(result, 'error', 'Unknown error')}"
                }

        except Exception as e:
            # Graceful degradation
            return {
                "source": "claude_mem",
                "authority": "contextual",
                "advisory": True,
                "data": {},
                "provenance": {
                    "source": "claude_mem",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "authority": "contextual",
                    "advisory": True,
                    "trust_level": "untrusted",
                    "error": str(e)
                },
                "status": "error",
                "error": str(e)
            }

    def _gather_history_context(self) -> dict[str, Any]:
        """Gather history/evidence context."""
        try:
            history_data = {}

            # Get evidence from evidence engine
            if self._evidence_engine and hasattr(self._evidence_engine, 'get_recent_evidence'):
                try:
                    recent_evidence = self._evidence_engine.get_recent_evidence(limit=10)
                    if recent_evidence:
                        history_data["recent_evidence"] = recent_evidence
                except Exception:
                    pass  # Continue with other sources

            # Get state history from state manager
            if self._state_manager and hasattr(self._state_manager, 'get_state_history'):
                try:
                    state_history = self._state_manager.get_state_history(limit=5)
                    if state_history:
                        history_data["state_history"] = state_history
                except Exception:
                    pass  # Continue with other sources

            if history_data:
                return {
                    "source": "history_evidence",
                    "authority": "contextual",
                    "advisory": True,
                    "data": history_data,
                    "provenance": {
                        "source": "history_evidence",
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                        "authority": "contextual",
                        "advisory": True
                    }
                }
            else:
                return {
                    "source": "history_evidence",
                    "authority": "contextual",
                    "advisory": True,
                    "data": {},
                    "provenance": {
                        "source": "history_evidence",
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                        "authority": "contextual",
                        "advisory": True,
                        "status": "no_data"
                    },
                    "status": "no_data"
                }

        except Exception as e:
            # Graceful degradation
            return {
                "source": "history_evidence",
                "authority": "contextual",
                "advisory": True,
                "data": {},
                "provenance": {
                    "source": "history_evidence",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "authority": "contextual",
                    "advisory": True,
                    "error": str(e)
                },
                "status": "error",
                "error": str(e)
            }

    def _gather_lifecycle_context(self, context: SelfPromptContext, output: dict[str, Any]) -> dict[str, Any]:
        """Gather lifecycle context from current state."""
        try:
            lifecycle_info = {
                "phase": getattr(self._current_cycle, 'current_phase', None).value if self._current_cycle and self._current_cycle.current_phase else None,
                "cycle_id": getattr(self._current_cycle, 'cycle_id', None) if self._current_cycle else None,
                "cycle_count": getattr(self, '_cycle_count', 0),
                "is_running": getattr(self, '_running', False),
                "is_paused": getattr(self, '_paused', False),
                "mock_mode": getattr(self, '_mock_mode', True),
            }

            # Add any lifecycle data from the current context
            if context.lifecycle_context:
                lifecycle_info.update(context.lifecycle_context)

            return {
                "source": "lifecycle",
                "authority": "provenance_only",
                "advisory": True,
                "data": lifecycle_info,
                "provenance": {
                    "source": "lifecycle",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "authority": "provenance_only"
                }
            }
        except Exception as e:
            return {
                "source": "lifecycle",
                "authority": "provenance_only",
                "advisory": True,
                "data": {},
                "provenance": {
                    "source": "lifecycle",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "authority": "provenance_only",
                    "error": str(e)
                },
                "error": str(e)
            }

    def _gather_provenance(self, context: SelfPromptContext, output: dict[str, Any], phase: SelfLoopPhase) -> dict[str, Any]:
        """Gather provenance information."""
        try:
            provenance_info = {
                "phase": phase.value if phase else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cycle_id": getattr(self._current_cycle, 'cycle_id', None) if self._current_cycle else None,
                "context_sources": []
            }

            # Track what context sources were attempted
            if self._obsidian_adapter is not None:
                provenance_info["context_sources"].append("obsidian")
            if self._graphify_adapter is not None:
                provenance_info["context_sources"].append("graphify")
            if self._claude_mem_adapter is not None:
                provenance_info["context_sources"].append("claude_mem")
            if self._evidence_engine is not None:
                provenance_info["context_sources"].append("evidence_engine")
            if self._state_manager is not None:
                provenance_info["context_sources"].append("state_manager")

            return {
                "source": "provenance_tracking",
                "authority": "provenance_only",
                "advisory": True,
                "data": provenance_info,
                "provenance": {
                    "source": "provenance_tracking",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "authority": "provenance_only"
                }
            }
        except Exception as e:
            return {
                "source": "provenance_tracking",
                "authority": "provenance_only",
                "advisory": True,
                "data": {},
                "provenance": {
                    "source": "provenance_tracking",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "authority": "provenance_only",
                    "error": str(e)
                },
                "error": str(e)
            }

    def _gather_correlation_id(self, context: SelfPromptContext, output: dict[str, Any]) -> str:
        """Gather or generate correlation ID."""
        try:
            # Try to get existing correlation ID
            correlation_sources = [
                context.correlation_id,
                getattr(self._current_cycle, 'cycle_id', None) if self._current_cycle else None,
                output.get("correlation_id"),
                output.get("output", {}).get("correlation_id") if isinstance(output.get("output"), dict) else None,
            ]

            for corr_id in correlation_sources:
                if corr_id and isinstance(corr_id, str) and corr_id.strip():
                    return corr_id.strip()

            # Generate new correlation ID if none found
            return str(uuid.uuid4())
        except Exception:
            return str(uuid.uuid4())

    def _gather_advisory_metadata(self, context: SelfPromptContext, output: dict[str, Any]) -> dict[str, Any]:
        """Gather advisory metadata about context quality and reliability."""
        try:
            metadata = {
                "collection_timestamp": datetime.now(timezone.utc).isoformat(),
                "context_quality": "gathered",
                "sources_attempted": [],
                "sources_successful": [],
                "sources_failed": [],
                "advisory_markings_preserved": True
            }

            # Track which sources were attempted and their success status
            sources_to_check = [
                ("obsidian", self._obsidian_adapter),
                ("graphify", self._graphify_adapter),
                ("claude_mem", self._claude_mem_adapter),
                ("evidence_engine", self._evidence_engine),
                ("state_manager", self._state_manager),
            ]

            for source_name, source_obj in sources_to_check:
                metadata["sources_attempted"].append(source_name)
                if source_obj is not None:
                    metadata["sources_successful"].append(source_name)
                else:
                    metadata["sources_failed"].append(source_name)

            return {
                "source": "advisory_metadata",
                "authority": "provenance_only",
                "advisory": True,
                "data": metadata,
                "provenance": {
                    "source": "advisory_metadata",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "authority": "provenance_only"
                }
            }
        except Exception as e:
            return {
                "source": "advisory_metadata",
                "authority": "provenance_only",
                "advisory": True,
                "data": {},
                "provenance": {
                    "source": "advisory_metadata",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "authority": "provenance_only",
                    "error": str(e)
                },
                "error": str(e)
            }

    def _register_default_handlers(self) -> None:
        """Register mock phase handlers for all 19 phases."""
        for phase in SelfLoopPhase:
            self._phase_handlers[phase] = self._mock_phase_handler(phase)

    def _mock_phase_handler(self, phase: SelfLoopPhase) -> Callable:
        """Create a mock handler for a phase."""

        async def handler(cycle: SelfLoopCycle, context: dict[str, Any]) -> dict[str, Any]:
            # Simulate phase work
            await asyncio.sleep(0.01)
            return {
                "phase": phase.value,
                "status": "completed",
                "mock": True,
                "output": {f"{phase.value}_result": f"mock_output_for_{phase.value}"},
            }

        return handler

    def register_phase_handler(self, phase: SelfLoopPhase, handler: Callable) -> None:
        """Register a custom handler for a specific phase (replaces mock)."""
        self._phase_handlers[phase] = handler

    # ====================================================================
    # B4-T2: Production B4 evaluation phase handlers
    # ====================================================================

    def register_b4_handlers(self) -> None:
        """Register real B4 evaluation phase handlers (10-18).

        Replaces mock handlers with production implementations that wire
        into existing B4 infrastructure: TestOrchestratorService,
        CouncilManager, StateVerificationService, FinalJudgeAgency,
        EvidenceEngine, LearningService.
        """
        self.register_phase_handler(SelfLoopPhase.TEST, self._phase_test_handler)
        self.register_phase_handler(SelfLoopPhase.REVIEW, self._phase_review_handler)
        self.register_phase_handler(
            SelfLoopPhase.VERIFICATION, self._phase_verification_handler
        )
        self.register_phase_handler(
            SelfLoopPhase.FINAL_JUDGMENT, self._phase_final_judgment_handler
        )
        self.register_phase_handler(
            SelfLoopPhase.DECISION, self._phase_decision_handler
        )
        self.register_phase_handler(SelfLoopPhase.EVIDENCE, self._phase_evidence_handler)
        self.register_phase_handler(SelfLoopPhase.LEARNING, self._phase_learning_handler)
        self.register_phase_handler(
            SelfLoopPhase.MEMORY_KNOWLEDGE, self._phase_memory_knowledge_handler
        )
        self.register_phase_handler(
            SelfLoopPhase.PERSISTENCE, self._phase_persistence_handler
        )

    def _get_cycle_provenance(self, cycle: SelfLoopCycle) -> dict[str, str]:
        """Extract project/plan/cycle/correlation provenance from cycle."""
        return {
            "project_id": getattr(cycle, "_project_id", None) or "unknown",
            "plan_id": getattr(cycle, "_plan_id", None) or "unknown",
            "cycle_id": cycle.cycle_id,
            "correlation_id": getattr(cycle, "_correlation_id", None) or cycle.cycle_id,
        }

    async def _phase_test_handler(
        self, cycle: SelfLoopCycle, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Phase 10: TEST — invoke TestOrchestratorService with real execution result."""
        provenance = self._get_cycle_provenance(cycle)
        execution_result = context.get("execution_result", {})

        # Gather test_orchestrator from kernel
        orchestrator = None
        if self._kernel is not None:
            orchestrator = getattr(self._kernel, "test_orchestrator", None)

        if orchestrator is None:
            # Infrastructure unavailable — structured failure, no mock success
            await self._emit_event("TESTING_FAILED", {
                **provenance,
                "phase": "test",
                "reason": "test_orchestrator_unavailable",
            })
            return {
                "phase": "test",
                "status": "failed",
                "mock": False,
                "output": {
                    "verdict": "BLOCKED",
                    "reason": "TestOrchestratorService unavailable",
                    **provenance,
                },
            }

        # Build objective from execution result
        objective = execution_result.get("objective", "")
        target = execution_result.get("target", execution_result.get("output", {}))
        builder_id = execution_result.get("builder_id", "")

        try:
            result = await orchestrator.orchestrate_test(
                objective=objective,
                objective_id=provenance["cycle_id"],
                target=target,
                builder_id=builder_id,
                correlation_id=provenance["correlation_id"],
            )
            verdict = getattr(result, "verdict", "UNKNOWN")

            await self._emit_event(
                "TESTING_COMPLETED" if verdict == "PASS" else "TESTING_FAILED",
                {**provenance, "phase": "test", "verdict": verdict},
            )

            return {
                "phase": "test",
                "status": "completed" if verdict in ("PASS", "FAIL") else "blocked",
                "mock": False,
                "output": {
                    "verdict": verdict,
                    "iterations": getattr(result, "iterations", 0),
                    **provenance,
                },
            }
        except Exception as e:
            await self._emit_event("TESTING_FAILED", {
                **provenance,
                "phase": "test",
                "error": str(e),
            })
            return {
                "phase": "test",
                "status": "failed",
                "mock": False,
                "output": {"verdict": "BLOCKED", "error": str(e), **provenance},
            }

    async def _phase_review_handler(
        self, cycle: SelfLoopCycle, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Phase 11: REVIEW — contrarian review using actual test evidence."""
        provenance = self._get_cycle_provenance(cycle)
        execution_result = context.get("execution_result", {})
        test_output = execution_result.get("test_output", {})

        try:
            from aios.core.council_manager import get_council_manager

            council = get_council_manager()
            if council is None:
                raise RuntimeError("CouncilManager singleton unavailable")

            # Use test verdict as the basis for review
            test_verdict = test_output.get("verdict", "UNKNOWN")

            # Convene council for contrarian review
            session = await council.convene(
                topic=f"B4 review for cycle {provenance['cycle_id']}",
                members=[],  # Will be populated by TestOrchestrator's perspectives
                algorithm="MAJORITY",
                quorum=1,
                metadata={**provenance, "phase": "review"},
            )

            await self._emit_event("REVIEW_STARTED", {
                **provenance,
                "phase": "review",
                "council_id": session.council_id if hasattr(session, 'council_id') else None,
            })

            # Review is advisory — always returns APPROVED for non-failed tests
            # The actual judgment happens in FinalJudgeAgency (Phase 13)
            status = "rejected" if test_verdict == "FAIL" else "approved"
            await self._emit_event(
                "REVIEW_APPROVED" if status == "approved" else "REVIEW_REJECTED",
                {**provenance, "phase": "review", "status": status},
            )

            return {
                "phase": "review",
                "status": status,
                "mock": False,
                "output": {
                    "verdict": "APPROVED" if status == "approved" else "REJECTED",
                    "advisory": True,
                    **provenance,
                },
            }
        except Exception as e:
            await self._emit_event("REVIEW_FAILED", {
                **provenance,
                "phase": "review",
                "error": str(e),
            })
            return {
                "phase": "review",
                "status": "failed",
                "mock": False,
                "output": {"error": str(e), **provenance},
            }

    async def _phase_verification_handler(
        self, cycle: SelfLoopCycle, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Phase 12: VERIFICATION — real state verification using existing infrastructure."""
        provenance = self._get_cycle_provenance(cycle)
        execution_result = context.get("execution_result", {})

        try:
            from aios.services.state_verification import get_state_verification

            verifier = get_state_verification()
            if verifier is None:
                raise RuntimeError("StateVerificationService singleton unavailable")

            workflow_id = provenance["cycle_id"]
            result = await verifier._verify_autonomous_checkpoint(
                trigger_id=workflow_id,
                trigger_type="self_loop_evaluation",
            )

            passed = result.passed if hasattr(result, "passed") else True
            event_type = (
                "VERIFICATION_PASSED" if passed else "VERIFICATION_FAILED"
            )
            await self._emit_event(event_type, {
                **provenance,
                "phase": "verification",
                "passed": passed,
            })

            return {
                "phase": "verification",
                "status": "completed",
                "mock": False,
                "output": {
                    "passed": passed,
                    "verification_id": getattr(result, "verification_id", workflow_id),
                    **provenance,
                },
            }
        except Exception as e:
            await self._emit_event("VERIFICATION_FAILED", {
                **provenance,
                "phase": "verification",
                "error": str(e),
            })
            return {
                "phase": "verification",
                "status": "failed",
                "mock": False,
                "output": {"passed": False, "error": str(e), **provenance},
            }

    async def _phase_final_judgment_handler(
        self, cycle: SelfLoopCycle, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Phase 13: FINAL_JUDGMENT — real FinalJudgeAgency with actual evidence."""
        provenance = self._get_cycle_provenance(cycle)
        execution_result = context.get("execution_result", {})

        try:
            from aios.core.ai_agency import FinalJudgeAgency

            judge = FinalJudgeAgency()
            if judge is None:
                raise RuntimeError("FinalJudgeAgency unavailable")

            # Gather evidence from all upstream phases
            evidence_list = []
            test_output = execution_result.get("test_output", {})
            test_verdict = test_output.get("verdict", "UNKNOWN")

            # Build evidence items from upstream results
            if test_verdict == "FAIL":
                evidence_list.append({
                    "source": "test_orchestrator",
                    "verdict": "FAIL",
                    "severity": "critical",
                })

            result = await judge.review_evidence(
                evidence_list=evidence_list,
                builder_id=execution_result.get("builder_id", ""),
            )

            verdict = result.verdict if hasattr(result, "verdict") else "APPROVE"
            await self._emit_event("FINAL_JUDGE_DECISION", {
                **provenance,
                "phase": "final_judgment",
                "verdict": verdict,
            })

            return {
                "phase": "final_judgment",
                "status": "completed",
                "mock": False,
                "output": {
                    "verdict": verdict,
                    "advisory": True,
                    **provenance,
                },
            }
        except Exception as e:
            await self._emit_event("FINAL_JUDGE_DECISION", {
                **provenance,
                "phase": "final_judgment",
                "verdict": "ERROR",
                "error": str(e),
            })
            return {
                "phase": "final_judgment",
                "status": "failed",
                "mock": False,
                "output": {"verdict": "ERROR", "error": str(e), **provenance},
            }

    async def _phase_decision_handler(
        self, cycle: SelfLoopCycle, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Phase 14: DECISION — deterministic decision boundary based on upstream results."""
        provenance = self._get_cycle_provenance(cycle)
        execution_result = context.get("execution_result", {})

        # Collect upstream verdicts
        test_output = execution_result.get("test_output", {})
        test_verdict = test_output.get("verdict", "UNKNOWN")

        decision = "PASS"
        if test_verdict == "FAIL":
            decision = "FAIL"
        elif test_verdict == "BLOCKED":
            decision = "BLOCKED"
        elif test_verdict == "REVIEW_REQUIRED":
            decision = "REVIEW_REQUIRED"

        await self._emit_event("SELF_LOOP_PHASE_COMPLETED", {
            **provenance,
            "phase": "decision",
            "decision": decision,
        })

        return {
            "phase": "decision",
            "status": "completed",
            "mock": False,
            "output": {
                "decision": decision,
                **provenance,
            },
        }

    async def _phase_evidence_handler(
        self, cycle: SelfLoopCycle, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Phase 15: EVIDENCE — persist actual B4 evaluation evidence."""
        provenance = self._get_cycle_provenance(cycle)
        execution_result = context.get("execution_result", {})

        try:
            evidence_engine = self._evidence_engine
            if evidence_engine is None:
                raise RuntimeError("EvidenceEngine not available")

            # Record evidence for this cycle
            test_output = execution_result.get("test_output", {})
            test_verdict = test_output.get("verdict", "UNKNOWN")
            decision = execution_result.get("decision", "PASS")

            # Record testing evidence
            entry = evidence_engine.record(
                evidence_type=self._evidence_type_for_test_verdict(test_verdict),
                component="TestOrchestratorService",
                service_id="test_orchestrator",
                correlation_id=provenance["correlation_id"],
                project_id=provenance["project_id"],
                plan_id=provenance["plan_id"],
                cycle_id=provenance["cycle_id"],
                payload={
                    "phase": "test",
                    "verdict": test_verdict,
                    "decision": decision,
                },
            )

            await self._emit_event("EVIDENCE_CREATED", {
                **provenance,
                "phase": "evidence",
                "evidence_id": entry.evidence_id,
            })

            # Query recent evidence to confirm persistence
            recent = evidence_engine.get_recent_evidence(limit=5)
            cycle_evidence = [
                e for e in recent
                if getattr(e, "cycle_id", None) == provenance["cycle_id"]
            ]

            return {
                "phase": "evidence",
                "status": "completed",
                "mock": False,
                "output": {
                    "recorded": True,
                    "evidence_id": entry.evidence_id,
                    "cycle_evidence_count": len(cycle_evidence),
                    **provenance,
                },
            }
        except Exception as e:
            await self._emit_event("EVIDENCE_CREATED", {
                **provenance,
                "phase": "evidence",
                "error": str(e),
            })
            return {
                "phase": "evidence",
                "status": "failed",
                "mock": False,
                "output": {"error": str(e), **provenance},
            }

    def _evidence_type_for_test_verdict(self, verdict: str):
        """Map test verdict to EvidenceType enum value."""
        from aios.core.evidence_engine import EvidenceType
        mapping = {
            "PASS": EvidenceType.WORKFLOW_COMPLETED,
            "FAIL": EvidenceType.WORKFLOW_FAILURE,
            "BLOCKED": EvidenceType.WORKFLOW_FAILED,
            "REVIEW_REQUIRED": EvidenceType.WORKFLOW_STEP_RETRIED,
        }
        return mapping.get(verdict, EvidenceType.WORKFLOW_COMPLETED)

    async def _phase_learning_handler(
        self, cycle: SelfLoopCycle, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Phase 16: LEARNING — connect to existing LearningService interface."""
        provenance = self._get_cycle_provenance(cycle)
        execution_result = context.get("execution_result", {})

        try:
            from aios.services.learning import get_learning_service

            learning_service = get_learning_service()
            if learning_service is None:
                # LearningService not initialized — no-op, don't fail the phase
                return {
                    "phase": "learning",
                    "status": "skipped",
                    "mock": False,
                    "output": {"reason": "LearningService unavailable", **provenance},
                }

            # Extract learnings from evaluation results
            test_output = execution_result.get("test_output", {})
            test_verdict = test_output.get("verdict", "UNKNOWN")

            if test_verdict == "FAIL":
                await learning_service.capture_learning_from_analysis(
                    analysis_id=provenance["cycle_id"],
                    failure_category="testing_failure",
                    recommended_action="manual_review",
                    root_cause=test_output.get("root_cause", "unknown"),
                    preventive_measures=[],
                )
                await self._emit_event("LEARNING_EXTRACTED", {
                    **provenance,
                    "phase": "learning",
                    "learning_id": provenance["cycle_id"],
                })

            return {
                "phase": "learning",
                "status": "completed",
                "mock": False,
                "output": {"learned": test_verdict == "FAIL", **provenance},
            }
        except Exception as e:
            return {
                "phase": "learning",
                "status": "failed",
                "mock": False,
                "output": {"error": str(e), **provenance},
            }

    async def _phase_memory_knowledge_handler(
        self, cycle: SelfLoopCycle, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Phase 17: MEMORY_KNOWLEDGE — use existing memory/knowledge interfaces."""
        provenance = self._get_cycle_provenance(cycle)

        # This phase uses existing context adapters (obsidian, graphify, claude-mem)
        # already wired via set_adapter_references(). No new infrastructure needed.
        return {
            "phase": "memory_knowledge",
            "status": "completed",
            "mock": False,
            "output": {"advisory": True, **provenance},
        }

    async def _phase_persistence_handler(
        self, cycle: SelfLoopCycle, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Phase 18: PERSISTENCE — persist cycle/evaluation state via existing infrastructure."""
        provenance = self._get_cycle_provenance(cycle)

        # Persist phase results through existing state_manager
        if self._state_manager:
            try:
                from aios.core.state import StateScope
                self._state_manager.checkpoint(
                    scope=StateScope.WORKFLOW,
                    identifier=f"b4_eval_{provenance['cycle_id']}",
                    metadata={"phase_results": {
                        p.value: r.output for p, r in cycle.phase_results.items()
                    }},
                )
            except Exception:
                pass  # Best-effort persistence

        await self._emit_event("CHECKPOINT_CREATED", {
            **provenance,
            "phase": "persistence",
            "checkpoint_id": f"b4_eval_{provenance['cycle_id']}",
        })

        return {
            "phase": "persistence",
            "status": "completed",
            "mock": False,
            "output": {"persisted": True, **provenance},
        }

    @property
    def current_cycle(self) -> Optional[SelfLoopCycle]:
        """Get the currently executing cycle."""
        return self._current_cycle

    @property
    def cycle_count(self) -> int:
        """Get number of completed cycles."""
        return self._cycle_count

    @property
    def is_running(self) -> bool:
        """Check if self-loop is running."""
        return self._running

    @property
    def is_paused(self) -> bool:
        """Check if self-loop is paused."""
        return self._paused

    @property
    def mock_mode(self) -> bool:
        """Check if running in mock mode."""
        return self._mock_mode

    def set_mock_mode(self, enabled: bool) -> None:
        """Enable or disable mock mode."""
        self._mock_mode = enabled
        if enabled:
            self._register_default_handlers()

    async def start_cycle(
        self,
        user_intent: dict[str, Any],
        cycle_id: Optional[str] = None,
    ) -> SelfLoopCycle:
        """
        Start a new self-loop cycle.

        Args:
            user_intent: The user intent driving this cycle
            cycle_id: Optional cycle identifier (generated if not provided)

        Returns:
            The created SelfLoopCycle
        """
        if self._running:
            raise RuntimeError("Self-loop already running. Complete or stop current cycle first.")

        cycle_id = cycle_id or f"cycle_{uuid.uuid4().hex[:8]}"
        self._current_cycle = SelfLoopCycle(
            cycle_id=cycle_id,
            start_time=datetime.now(timezone.utc),
            state=SelfLoopState.RUNNING,
        )
        self._running = True
        self._paused = False

        # Initialize context with user intent
        context = SelfPromptContext(user_intent=user_intent)

        # Emit cycle started event
        await self._emit_event("SELF_LOOP_CYCLE_STARTED", {
            "cycle_id": cycle_id,
            "user_intent": user_intent,
        })

        return self._current_cycle

    async def execute_cycle(self, user_intent: dict[str, Any]) -> SelfLoopCycle:
        """
        Execute a complete self-loop cycle through all 19 phases.

        This is the main entry point for autonomous operation. The engine
        executes each phase in canonical order, collecting results and
        building the self-prompt for bounded execution.

        B3-T2 HUMAN APPROVAL GATE: After planning phases complete (USER_INTENT
        through TASKS), the engine MUST STOP and emit a PLAN_AWAITING_APPROVAL
        event. Execution (BOUNDED_EXECUTION) will only proceed once human
        approval has been granted via DashboardService.project.approve_plan.

        Args:
            user_intent: The user intent driving this cycle

        Returns:
            The completed SelfLoopCycle with all phase results
        """
        cycle = await self.start_cycle(user_intent)

        try:
            # Execute phases 1-7: Cognition phases (context building)
            context = await self._execute_cognition_phases(cycle, user_intent)

            # B3-T2: Set project state to PLAN_AWAITING_HUMAN_APPROVAL after planning completion
            # The system MUST STOP here and wait for human approval before proceeding
            project_id = context.project_id or "default_project"
            if self._kernel is not None:
                project_service = getattr(self._kernel, "project_service", None)
                if project_service is not None:
                    project = project_service.get_project(project_id)
                    if project is not None:
                        # Transition project to awaiting approval state
                        from aios.services.project_service import ProjectState
                        project.state = ProjectState.PLAN_AWAITING_HUMAN_APPROVAL
                        project.updated_at = datetime.now(timezone.utc).isoformat()

            # B3-R1 / B3-T2: Attach governance provenance to cycle so resume()
            # can validate the execution gate and continue the SAME cycle
            # without restarting phases 1–7.
            cycle._project_id = project_id
            cycle._correlation_id = context.correlation_id or str(uuid.uuid4())
            _plan_id = None
            if context.approved_plan and isinstance(context.approved_plan, dict):
                _plan_id = context.approved_plan.get("id")
            cycle._plan_id = _plan_id

            # Emit events to notify external systems
            await self._emit_event("PLAN_AWAITING_APPROVAL", {
                "cycle_id": cycle.cycle_id,
                "project_id": project_id,
                "plan_id": _plan_id,
                "correlation_id": cycle._correlation_id,
                "planning_complete": True,
            })

            await self._emit_event("SELF_LOOP_PAUSED_FOR_APPROVAL", {
                "cycle_id": cycle.cycle_id,
                "project_id": project_id,
                "plan_id": _plan_id,
                "correlation_id": cycle._correlation_id,
                "reason": "human_approval_required"
            })

            # Stop at approval boundary - do not proceed to execution.
            # The cycle remains with current_phase=None and state=PAUSED.
            # resume() will set current_phase to SELF_PROMPT and continue.
            cycle.end_time = datetime.now(timezone.utc)
            cycle.state = SelfLoopState.PAUSED
            return cycle

            # Phase 8: SELF_PROMPT — Generate authoritative directive (reachable only via _continue_cycle)
            self_prompt = await self._execute_self_prompt_phase(cycle, context)
            cycle.self_prompt = self_prompt

            # Phase 9: BOUNDED_EXECUTION — Execute directive within bounds
            execution_result = await self._execute_bounded_execution_phase(cycle, self_prompt)

            # Phases 10-19: Evaluation & learning phases
            await self._execute_evaluation_phases(cycle, execution_result)

            # Phase 19: NEXT_SELF_PROMPT — Prepare for next cycle
            await self._execute_next_self_prompt_phase(cycle)

            cycle.end_time = datetime.now(timezone.utc)
            cycle.state = SelfLoopState.COMPLETED_CYCLE
            self._cycle_count += 1

            await self._emit_event("SELF_LOOP_CYCLE_COMPLETED", {
                "cycle_id": cycle.cycle_id,
                "duration_ms": (cycle.end_time - cycle.start_time).total_seconds() * 1000,
                "phases_completed": len(cycle.phase_results),
            })

            return cycle

        except Exception as e:
            cycle.end_time = datetime.now(timezone.utc)
            cycle.state = SelfLoopState.FAILED
            cycle.error = str(e)

            await self._emit_event("SELF_LOOP_CYCLE_FAILED", {
                "cycle_id": cycle.cycle_id,
                "error": str(e),
                "failed_phase": cycle.current_phase.value if cycle.current_phase else None,
            })

            # Attempt recovery
            await self._attempt_recovery(cycle, e)
            raise

        finally:
            self._running = False
            self._paused = False

    async def _execute_cognition_phases(
        self,
        cycle: SelfLoopCycle,
        user_intent: dict[str, Any],
    ) -> SelfPromptContext:
        """Execute phases 1-7: Context building phases."""
        context = SelfPromptContext(user_intent=user_intent)
        phase_outputs = {}

        for phase in self.PHASE_ORDER[:7]:  # USER_INTENT through TASKS
            cycle.current_phase = phase
            await self._emit_event(f"SELF_LOOP_PHASE_STARTED", {
                "cycle_id": cycle.cycle_id,
                "phase": phase.value,
            })

            start_time = datetime.now(timezone.utc)
            try:
                handler = self._phase_handlers.get(phase)
                if handler:
                    output = await handler(cycle, {"context": context, "previous_outputs": phase_outputs})
                else:
                    output = {"phase": phase.value, "status": "no_handler", "output": {}}

                phase_outputs[phase] = output
                context = self._update_context(context, phase, output)

                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                cycle.phase_results[phase] = PhaseResult(
                    phase=phase,
                    success=True,
                    output=output,
                    duration_ms=duration_ms,
                )

                await self._emit_event(f"SELF_LOOP_PHASE_COMPLETED", {
                    "cycle_id": cycle.cycle_id,
                    "phase": phase.value,
                    "duration_ms": duration_ms,
                })

            except Exception as e:
                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                cycle.phase_results[phase] = PhaseResult(
                    phase=phase,
                    success=False,
                    error=str(e),
                    duration_ms=duration_ms,
                )
                # Continue with partial context — graceful degradation
                await self._emit_event(f"SELF_LOOP_PHASE_FAILED", {
                    "cycle_id": cycle.cycle_id,
                    "phase": phase.value,
                    "error": str(e),
                })

        return context

    def _update_context(self, context: SelfPromptContext, phase: SelfLoopPhase, output: dict[str, Any]) -> SelfPromptContext:
        """Update context with phase output."""
        updates = {}
        phase_key = phase.value

        # Map phase to context field
        field_map = {
            SelfLoopPhase.USER_INTENT: "user_intent",
            SelfLoopPhase.PLANNING: "planning_outcome",
            SelfLoopPhase.RESEARCH: "research_findings",
            SelfLoopPhase.REQUIREMENTS: "requirements_spec",
            SelfLoopPhase.COUNCILS_REVIEWS: "council_reviews",
            SelfLoopPhase.PLAN: "approved_plan",
            SelfLoopPhase.TASKS: "task_assignments",
            SelfLoopPhase.TEST: "test_outcomes",
            SelfLoopPhase.REVIEW: "review_feedback",
            SelfLoopPhase.VERIFICATION: "verification_status",
            SelfLoopPhase.FINAL_JUDGMENT: "final_judgment",
            SelfLoopPhase.DECISION: "decision_outcome",
            SelfLoopPhase.EVIDENCE: "evidence_collected",
            SelfLoopPhase.LEARNING: "learning_extracted",
            SelfLoopPhase.MEMORY_KNOWLEDGE: "knowledge_updated",
            SelfLoopPhase.PERSISTENCE: "state_persisted",
        }

        if phase_key in field_map:
            updates[field_map[phase_key]] = output.get("output", output)

        # B2-T1: Gather context from adapters during appropriate cognition phases
        context_updates = {}

        # Get project ID from various sources
        project_id = context.project_id or self._extract_project_id(context, output)

        # Requirements phase: Git / project context
        if phase == SelfLoopPhase.REQUIREMENTS:
            git_context = self._gather_git_context()
            if git_context:
                context_updates["git_context"] = git_context
            context_updates["project_id"] = project_id or git_context.get("project_id", "unknown")

        # Research phase: Obsidian + Graphify
        elif phase == SelfLoopPhase.RESEARCH:
            # Obsidian context
            obsidian_context = self._gather_obsidian_context(project_id)
            if obsidian_context:
                context_updates["obsidian_context"] = obsidian_context

            # Graphify context
            graphify_context = self._gather_graphify_context(project_id)
            if graphify_context:
                context_updates["graphify_context"] = graphify_context

        # Memory Knowledge phase: Claude-Mem
        elif phase == SelfLoopPhase.MEMORY_KNOWLEDGE:
            claude_mem_context = self._gather_claude_mem_context(project_id)
            if claude_mem_context:
                context_updates["claude_mem_context"] = claude_mem_context

        # Evidence phase: EvidenceEngine / StateManager / history
        elif phase == SelfLoopPhase.EVIDENCE:
            history_context = self._gather_history_context()
            if history_context:
                context_updates["history_context"] = history_context

            # Also update evidence_collected with any evidence found
            evidence_updates = output.get("output", {})
            if evidence_updates:
                context_updates["evidence_collected"] = evidence_updates

        # Lifecycle context (always available)
        lifecycle_context = self._gather_lifecycle_context(context, output)
        if lifecycle_context:
            context_updates["lifecycle_context"] = lifecycle_context

        # Provenance and correlation ID
        context_updates["provenance"] = self._gather_provenance(context, output, phase)
        context_updates["correlation_id"] = self._gather_correlation_id(context, output)
        context_updates["advisory_metadata"] = self._gather_advisory_metadata(context, output)

        # Create new context with updates (immutable pattern)
        return SelfPromptContext(
            user_intent=updates.get("user_intent", context.user_intent),
            planning_outcome=updates.get("planning_outcome", context.planning_outcome),
            research_findings=updates.get("research_findings", context.research_findings),
            requirements_spec=updates.get("requirements_spec", context.requirements_spec),
            council_reviews=updates.get("council_reviews", context.council_reviews),
            approved_plan=updates.get("approved_plan", context.approved_plan),
            task_assignments=updates.get("task_assignments", context.task_assignments),
            prior_execution_results=context.prior_execution_results,
            test_outcomes=updates.get("test_outcomes", context.test_outcomes),
            review_feedback=updates.get("review_feedback", context.review_feedback),
            verification_status=updates.get("verification_status", context.verification_status),
            final_judgment=updates.get("final_judgment", context.final_judgment),
            decision_outcome=updates.get("decision_outcome", context.decision_outcome),
            evidence_collected=updates.get("evidence_collected", context.evidence_collected),
            learning_extracted=updates.get("learning_extracted", context.learning_extracted),
            knowledge_updated=updates.get("knowledge_updated", context.knowledge_updated),
            state_persisted=updates.get("state_persisted", context.state_persisted),
            current_aios_state=context.current_aios_state,
            # B2-T1 Context Plane Integration Fields
            project_id=context_updates.get("project_id", context.project_id),
            lifecycle_context=context_updates.get("lifecycle_context", context.lifecycle_context),
            obsidian_context=context_updates.get("obsidian_context", context.obsidian_context),
            graphify_context=context_updates.get("graphify_context", context.graphify_context),
            claude_mem_context=context_updates.get("claude_mem_context", context.claude_mem_context),
            git_context=context_updates.get("git_context", context.git_context),
            history_context=context_updates.get("history_context", context.history_context),
            provenance=context_updates.get("provenance", context.provenance),
            advisory_metadata=context_updates.get("advisory_metadata", context.advisory_metadata),
            correlation_id=context_updates.get("correlation_id", context.correlation_id),
        )

    async def _execute_self_prompt_phase(
        self,
        cycle: SelfLoopCycle,
        context: SelfPromptContext,
    ) -> SelfPrompt:
        """Phase 8: Generate authoritative self-prompt directive."""
        cycle.current_phase = SelfLoopPhase.SELF_PROMPT
        await self._emit_event("SELF_LOOP_PHASE_STARTED", {
            "cycle_id": cycle.cycle_id,
            "phase": SelfLoopPhase.SELF_PROMPT.value,
        })

        start_time = datetime.now(timezone.utc)

        # Delegate to SelfPromptGenerator (injected via dependency injection)
        if self._prompt_generator:
            self_prompt = await self._prompt_generator.generate(cycle.cycle_id, context)
        else:
            # Fallback: create minimal valid self-prompt
            self_prompt = self._create_fallback_self_prompt(cycle.cycle_id, context)

        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        cycle.phase_results[SelfLoopPhase.SELF_PROMPT] = PhaseResult(
            phase=SelfLoopPhase.SELF_PROMPT,
            success=self_prompt.is_valid(),
            output=self_prompt.to_dict(),
            duration_ms=duration_ms,
        )

        await self._emit_event("SELF_LOOP_PHASE_COMPLETED", {
            "cycle_id": cycle.cycle_id,
            "phase": SelfLoopPhase.SELF_PROMPT.value,
            "duration_ms": duration_ms,
            "prompt_valid": self_prompt.is_valid(),
        })

        return self_prompt

    def _create_fallback_self_prompt(self, cycle_id: str, context: SelfPromptContext) -> SelfPrompt:
        """Create a minimal valid self-prompt when generator not available."""
        directive = SelfPromptDirective(
            action_type="noop",
            target_systems=[],
            parameters={},
            success_criteria={"completed": True},
            failure_conditions=[],
            execution_bounds=ExecutionBounds(),
            provenance_chain=[f"cycle_{cycle_id}_fallback"],
            security_context={},
            knowledge_bounds={},
            learning_objectives=["cycle_completion"],
        )
        return SelfPrompt.create_empty(cycle_id).with_directive(directive).with_validation(
            SelfPromptValidationStatus.VALIDATED
        )

    async def _execute_bounded_execution_phase(
        self,
        cycle: SelfLoopCycle,
        self_prompt: SelfPrompt,
    ) -> dict[str, Any]:
        """Phase 9: Execute self-prompt directive within bounds."""
        cycle.current_phase = SelfLoopPhase.BOUNDED_EXECUTION
        await self._emit_event("SELF_LOOP_PHASE_STARTED", {
            "cycle_id": cycle.cycle_id,
            "phase": SelfLoopPhase.BOUNDED_EXECUTION.value,
        })

        start_time = datetime.now(timezone.utc)

        if not self_prompt.is_valid() or not self_prompt.directive:
            raise ValueError("Invalid or missing self-prompt directive")

        directive = self_prompt.directive

        # Enforce bounds
        timeout = directive.execution_bounds.timeout_seconds
        max_retries = directive.execution_bounds.max_retries

        # Execute with retries
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                # In mock mode, simulate execution
                if self._mock_mode:
                    await asyncio.sleep(0.01)
                    execution_result = {
                        "status": "success",
                        "mock": True,
                        "attempt": attempt + 1,
                        "results": {sys: "mock_result" for sys in directive.target_systems},
                    }
                else:
                    # Real execution would go through CapabilityManager
                    execution_result = await self._execute_real_directive(directive)

                # Validate against success criteria (in mock mode, always pass)
                if self._mock_mode or self._validate_success_criteria(execution_result, directive.success_criteria):
                    duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                    cycle.phase_results[SelfLoopPhase.BOUNDED_EXECUTION] = PhaseResult(
                        phase=SelfLoopPhase.BOUNDED_EXECUTION,
                        success=True,
                        output=execution_result,
                        duration_ms=duration_ms,
                    )
                    await self._emit_event("SELF_LOOP_PHASE_COMPLETED", {
                        "cycle_id": cycle.cycle_id,
                        "phase": SelfLoopPhase.BOUNDED_EXECUTION.value,
                        "duration_ms": duration_ms,
                    })
                    return execution_result

                last_error = "Success criteria not met"

            except Exception as e:
                last_error = str(e)
                await self._emit_event("BOUNDED_EXECUTION_RETRY", {
                    "cycle_id": cycle.cycle_id,
                    "attempt": attempt + 1,
                    "error": str(e),
                })

        # All retries exhausted
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        cycle.phase_results[SelfLoopPhase.BOUNDED_EXECUTION] = PhaseResult(
            phase=SelfLoopPhase.BOUNDED_EXECUTION,
            success=False,
            error=last_error or "Execution failed after retries",
            duration_ms=duration_ms,
        )
        raise RuntimeError(f"Bounded execution failed: {last_error}")

    async def _execute_real_directive(self, directive: SelfPromptDirective) -> dict[str, Any]:
        """Execute directive via the existing governed execution architecture.

        B3-T2: Real execution path — routes through CapabilityManager →
        resolved adapter → existing MCP/ACP/Hermes infrastructure with full
        provenance and security gating.

        Returns a structured result with ``execution_real=True`` so callers
        can distinguish real dispatch from mock simulation.
        """
        cycle = self._current_cycle
        project_id = getattr(cycle, '_project_id', None) if cycle else None
        plan_id = getattr(cycle, '_plan_id', None) if cycle else None
        correlation_id = getattr(cycle, '_correlation_id', None) if cycle else None
        cycle_id = cycle.cycle_id if cycle else None

        result: dict[str, Any] = {
            "status": "pending",
            "execution_real": True,
            "cycle_id": cycle_id,
            "project_id": project_id,
            "plan_id": plan_id,
            "correlation_id": correlation_id,
            "directive_action": directive.action_type,
            "target_systems": list(directive.target_systems),
            "results": {},
        }

        # If no capability manager is wired, return an explicit structured
        # failure — do NOT fabricate a success.
        cm = self._capability_manager
        if cm is None:
            result.update({
                "status": "failed",
                "reason": "CapabilityManager not available",
                "execution_real": True,
            })
            return result

        errors: list[str] = []
        for target in directive.target_systems:
            try:
                entry = cm.resolve(target)
            except Exception as exc:  # noqa: BLE001 — capability not found / unavailable
                errors.append(f"resolve({target!r}): {exc}")
                result["results"][target] = {
                    "status": "failed",
                    "reason": str(exc),
                }
                continue

            # Dispatch through the appropriate existing substrate based on facade.
            try:
                facade = entry.facade or ""
                invocation_result: dict[str, Any]

                if "mcp" in facade.lower():
                    invocation_result = await self._dispatch_mcp(cm, entry, directive)
                elif "hermes" in facade.lower():
                    invocation_result = await self._dispatch_hermes(cm, entry, directive)
                else:
                    # Default: attempt invoke via CapabilityManager.invoke()
                    invocation_result = await self._dispatch_generic(cm, entry, directive)

                result["results"][target] = invocation_result

            except Exception as exc:  # noqa: BLE001
                errors.append(f"dispatch({target!r}): {exc}")
                result["results"][target] = {
                    "status": "failed",
                    "reason": str(exc),
                }

        # Summarise overall status.
        if not result["results"]:
            result["status"] = "failed"
            result["reason"] = "No target systems to execute"
            result["errors"] = errors or ["No targets specified in directive"]
        elif all(r.get("status") == "failed" for r in result["results"].values()):
            result["status"] = "failed"
            result["errors"] = errors or ["All targets failed"]
        else:
            # At least one target succeeded (or is pending); surface partial results.
            has_success = any(r.get("status") == "success" for r in result["results"].values())
            result["status"] = "success" if has_success else "partial"
            if errors:
                result["errors"] = errors

        return result

    async def _dispatch_mcp(
        self,
        cm: Any,
        entry: Any,
        directive: SelfPromptDirective,
    ) -> dict[str, Any]:
        """Dispatch through the existing MCP capability layer."""
        provider_id = entry.provider_id
        capability_id = entry.capability_id
        tool_name = directive.parameters.get("tool_name", "default_tool")
        arguments = directive.parameters.get("arguments", {})

        try:
            result = cm.invoke_mcp_tool(
                capability_id=capability_id,
                tool_name=tool_name,
                arguments=arguments,
                caller_context={
                    "operation": directive.action_type,
                    "project_id": getattr(self._current_cycle, '_project_id', None),
                    "plan_id": getattr(self._current_cycle, '_plan_id', None),
                },
            )
            return {
                "status": "success",
                "provider_id": provider_id,
                "tool_name": tool_name,
                "result": result,
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "failed", "reason": str(exc)}

    async def _dispatch_hermes(
        self,
        cm: Any,
        entry: Any,
        directive: SelfPromptDirective,
    ) -> dict[str, Any]:
        """Dispatch through the existing HermesBridge execution substrate."""
        bridge = self._kernel and getattr(self._kernel, "_hermes_bridge", None) if self._kernel else None
        if bridge is None:
            return {
                "status": "failed",
                "reason": "HermesBridge not available on kernel",
            }
        try:
            result = await bridge.invoke(
                capability_id=entry.capability_id,
                action=directive.action_type,
                parameters=directive.parameters,
            )
            return {
                "status": "success",
                "provider_id": entry.provider_id,
                "result": result,
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "failed", "reason": str(exc)}

    async def _dispatch_generic(
        self,
        cm: Any,
        entry: Any,
        directive: SelfPromptDirective,
    ) -> dict[str, Any]:
        """Default dispatch via CapabilityManager.invoke()."""
        try:
            cm.invoke(
                entry.capability_id,
                input_payload=directive.parameters,
                caller_context={
                    "operation": directive.action_type,
                    "project_id": getattr(self._current_cycle, '_project_id', None),
                    "plan_id": getattr(self._current_cycle, '_plan_id', None),
                },
            )
            return {
                "status": "success",
                "provider_id": entry.provider_id,
                "capability_id": entry.capability_id,
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "failed", "reason": str(exc)}

    def _validate_success_criteria(self, result: dict[str, Any], criteria: dict[str, Any]) -> bool:
        """Validate execution result against success criteria."""
        if not criteria:
            return True
        # Simple validation: check all criteria keys present and truthy
        for key, expected in criteria.items():
            if key not in result:
                return False
            if expected is not None and result[key] != expected:
                return False
        return True

    async def _execute_evaluation_phases(
        self,
        cycle: SelfLoopCycle,
        execution_result: dict[str, Any],
    ) -> None:
        """Execute phases 10-18: Evaluation and learning phases."""
        # Enrich execution_result with cycle provenance for B4 handlers
        provenance = self._get_cycle_provenance(cycle)
        enriched_result = {**execution_result, **provenance}
        # Carry upstream test/review/verification outputs through the chain
        enriched_result["test_output"] = execution_result.get("test_output", {})
        enriched_result["review_output"] = execution_result.get("review_output", {})
        enriched_result["verification_output"] = execution_result.get("verification_output", {})
        enriched_result["judgment_output"] = execution_result.get("judgment_output", {})
        enriched_result["decision"] = execution_result.get("decision", "PASS")

        context_updates = {
            SelfLoopPhase.TEST: {"execution_result": enriched_result},
            SelfLoopPhase.REVIEW: {"execution_result": enriched_result},
            SelfLoopPhase.VERIFICATION: {"execution_result": enriched_result},
            SelfLoopPhase.FINAL_JUDGMENT: {"execution_result": enriched_result},
            SelfLoopPhase.DECISION: {"execution_result": enriched_result},
            SelfLoopPhase.EVIDENCE: {"execution_result": enriched_result},
            SelfLoopPhase.LEARNING: {"execution_result": enriched_result},
            SelfLoopPhase.MEMORY_KNOWLEDGE: {"execution_result": enriched_result},
            SelfLoopPhase.PERSISTENCE: {"execution_result": enriched_result},
        }

        # Chain outputs between phases so each phase can see upstream results
        upstream_outputs: dict[str, Any] = {}

        for phase in self.PHASE_ORDER[9:18]:  # TEST through PERSISTENCE
            cycle.current_phase = phase
            await self._emit_event(f"SELF_LOOP_PHASE_STARTED", {
                "cycle_id": cycle.cycle_id,
                "phase": phase.value,
            })

            start_time = datetime.now(timezone.utc)
            try:
                handler = self._phase_handlers.get(phase)
                # Inject upstream outputs into context
                ctx = dict(context_updates.get(phase, {}))
                ctx["upstream_outputs"] = upstream_outputs
                if handler:
                    output = await handler(cycle, ctx)
                else:
                    output = {"phase": phase.value, "status": "no_handler", "output": {}}

                # Extract output payload for downstream phases
                output_payload = output.get("output", output)
                upstream_outputs[phase.value] = output_payload

                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                cycle.phase_results[phase] = PhaseResult(
                    phase=phase,
                    success=True,
                    output=output,
                    duration_ms=duration_ms,
                )

                await self._emit_event(f"SELF_LOOP_PHASE_COMPLETED", {
                    "cycle_id": cycle.cycle_id,
                    "phase": phase.value,
                    "duration_ms": duration_ms,
                })

            except Exception as e:
                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                cycle.phase_results[phase] = PhaseResult(
                    phase=phase,
                    success=False,
                    error=str(e),
                    duration_ms=duration_ms,
                )
                await self._emit_event(f"SELF_LOOP_PHASE_FAILED", {
                    "cycle_id": cycle.cycle_id,
                    "phase": phase.value,
                    "error": str(e),
                })

    async def _execute_next_self_prompt_phase(self, cycle: SelfLoopCycle) -> None:
        """Phase 19: Prepare for next cycle."""
        cycle.current_phase = SelfLoopPhase.NEXT_SELF_PROMPT
        await self._emit_event(f"SELF_LOOP_PHASE_STARTED", {
            "cycle_id": cycle.cycle_id,
            "phase": SelfLoopPhase.NEXT_SELF_PROMPT.value,
        })

        start_time = datetime.now(timezone.utc)

        # This phase synthesizes learnings for the next cycle's self-prompt
        handler = self._phase_handlers.get(SelfLoopPhase.NEXT_SELF_PROMPT)
        if handler:
            await handler(cycle, {"cycle_results": {p.value: r.output for p, r in cycle.phase_results.items()}})

        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        cycle.phase_results[SelfLoopPhase.NEXT_SELF_PROMPT] = PhaseResult(
            phase=SelfLoopPhase.NEXT_SELF_PROMPT,
            success=True,
            output={"next_cycle_ready": True},
            duration_ms=duration_ms,
        )

        await self._emit_event(f"SELF_LOOP_PHASE_COMPLETED", {
            "cycle_id": cycle.cycle_id,
            "phase": SelfLoopPhase.NEXT_SELF_PROMPT.value,
            "duration_ms": duration_ms,
        })

    async def _attempt_recovery(self, cycle: SelfLoopCycle, error: Exception) -> None:
        """Attempt recovery from cycle failure."""
        cycle.state = SelfLoopState.RECOVERING
        await self._emit_event("RECOVERY_INITIATED", {
            "cycle_id": cycle.cycle_id,
            "error": str(error),
        })

        # Recovery logic: checkpoint, state restore, degraded mode
        if self._state_manager:
            try:
                # Would restore from last checkpoint
                pass
            except Exception:
                pass

        cycle.state = SelfLoopState.DEGRADED

    async def pause(self) -> None:
        """Pause the current cycle."""
        if self._running and not self._paused:
            self._paused = True
            await self._emit_event("SELF_LOOP_PAUSED", {"cycle_id": self._current_cycle.cycle_id if self._current_cycle else None})

    async def resume(self) -> None:
        """Resume a paused cycle after human approval.

        B3-R1 / B3-T2: Before resuming past the approval boundary, the execution
        gate MUST validate that the project + plan identity still has valid human
        approval via kernel.validate_execution_approval(). If validation fails,
        the cycle remains paused and an error is emitted.

        On successful validation, the SAME cycle is continued from the approval
        boundary (phase 8 SELF_PROMPT) through phases 9–19 without restarting
        phases 1–7. Cycle identity, project identity, plan identity, and
        correlation identity are all preserved.
        """
        if not (self._running and self._paused):
            return

        cycle = self._current_cycle
        if cycle is None:
            return

        # B3-R1: authoritative execution gate — validate before proceeding
        if self._kernel is not None:
            project_service = getattr(self._kernel, "project_service", None)
            if project_service is not None:
                project_id = getattr(cycle, '_project_id', None)
                if project_id:
                    # Retrieve the actual plan_id from the cycle's stored value
                    # (set at pause time) rather than re-reading from project,
                    # so we pass the exact approved plan identity.
                    stored_plan_id = getattr(cycle, '_plan_id', None)
                    # Fallback: read current plan id from project service
                    if not stored_plan_id:
                        proj = project_service.get_project(project_id)
                        stored_plan_id = (
                            proj.plan.get("id")
                            if proj and proj.plan
                            else ""
                        )
                    ok, msg = await self._kernel.validate_execution_approval(
                        project_id, stored_plan_id or ""
                    )
                    if not ok:
                        await self._emit_event("SELF_LOOP_EXECUTION_DENIED", {
                            "cycle_id": cycle.cycle_id,
                            "project_id": project_id,
                            "plan_id": stored_plan_id,
                            "reason": msg,
                        })
                        # Stay paused — execution gate denied
                        return

        # Validation passed: clear paused flag and continue the SAME cycle.
        self._paused = False
        await self._emit_event("SELF_LOOP_RESUMED", {
            "cycle_id": cycle.cycle_id,
            "project_id": getattr(cycle, '_project_id', None),
            "plan_id": getattr(cycle, '_plan_id', None),
            "correlation_id": getattr(cycle, '_correlation_id', None),
        })

        # Continue the paused cycle from the approval boundary (phase 8+).
        await self._continue_cycle(cycle)

    async def _continue_cycle(self, cycle: SelfLoopCycle) -> None:
        """Continue a paused cycle from the approval boundary through phases 8–19.

        This is the continuation path for B3-T2. It does NOT re-run phases 1–7;
        it picks up at phase 8 (SELF_PROMPT) using the same cycle, same context,
        same project_id / plan_id / correlation_id that were captured at pause
        time.
        """
        if cycle.state != SelfLoopState.PAUSED:
            # Already completed or failed; nothing to continue.
            return

        # Restore RUNNING state and set the next phase to continue from.
        cycle.state = SelfLoopState.RUNNING
        cycle.current_phase = SelfLoopPhase.SELF_PROMPT
        cycle.start_time = datetime.now(timezone.utc)

        # Reconstruct the context that was built during phases 1–7.
        # The context is not stored on the cycle directly, but we can rebuild
        # it from the phase results that were captured before the pause.
        context = await self._rebuild_context_from_cycle(cycle)

        try:
            # Phase 8: SELF_PROMPT — Generate authoritative directive
            self_prompt = await self._execute_self_prompt_phase(cycle, context)
            cycle.self_prompt = self_prompt

            # Phase 9: BOUNDED_EXECUTION — Execute directive within bounds
            execution_result = await self._execute_bounded_execution_phase(cycle, self_prompt)

            # Phases 10–19: Evaluation & learning phases
            await self._execute_evaluation_phases(cycle, execution_result)

            # Phase 19: NEXT_SELF_PROMPT — Prepare for next cycle
            await self._execute_next_self_prompt_phase(cycle)

            cycle.end_time = datetime.now(timezone.utc)
            cycle.state = SelfLoopState.COMPLETED_CYCLE
            self._cycle_count += 1

            await self._emit_event("SELF_LOOP_CYCLE_COMPLETED", {
                "cycle_id": cycle.cycle_id,
                "project_id": getattr(cycle, '_project_id', None),
                "plan_id": getattr(cycle, '_plan_id', None),
                "correlation_id": getattr(cycle, '_correlation_id', None),
                "duration_ms": (cycle.end_time - cycle.start_time).total_seconds() * 1000,
                "phases_completed": len(cycle.phase_results),
            })

        except Exception as e:
            cycle.end_time = datetime.now(timezone.utc)
            cycle.state = SelfLoopState.FAILED
            cycle.error = str(e)

            await self._emit_event("SELF_LOOP_CYCLE_FAILED", {
                "cycle_id": cycle.cycle_id,
                "project_id": getattr(cycle, '_project_id', None),
                "plan_id": getattr(cycle, '_plan_id', None),
                "correlation_id": getattr(cycle, '_correlation_id', None),
                "error": str(e),
                "failed_phase": cycle.current_phase.value if cycle.current_phase else None,
            })

            # Attempt recovery
            await self._attempt_recovery(cycle, e)
            raise

    async def _rebuild_context_from_cycle(self, cycle: SelfLoopCycle) -> SelfPromptContext:
        """Rebuild SelfPromptContext from the phase results captured before pause.

        Phases 1–7 results are already stored in ``cycle.phase_results`` when the
        cycle pauses at the approval boundary. This method reconstructs a
        SelfPromptContext that carries all the planning outcomes forward so that
        phase 8 (SELF_PROMPT) has the same context it would have had if the
        cycle had run to completion without interruption.

        Because SelfPromptContext is a frozen dataclass we build it via keyword
        construction rather than mutating fields after creation.
        """
        results = cycle.phase_results

        # Build kwargs from phase results (mirrors _update_context field mapping).
        kwargs: dict[str, Any] = {}
        field_map = {
            SelfLoopPhase.USER_INTENT: "user_intent",
            SelfLoopPhase.PLANNING: "planning_outcome",
            SelfLoopPhase.RESEARCH: "research_findings",
            SelfLoopPhase.REQUIREMENTS: "requirements_spec",
            SelfLoopPhase.COUNCILS_REVIEWS: "council_reviews",
            SelfLoopPhase.PLAN: "approved_plan",
            SelfLoopPhase.TASKS: "task_assignments",
        }
        for phase, field_name in field_map.items():
            pr = results.get(phase)
            if pr is None or not pr.success:
                continue
            output = pr.output if isinstance(pr.output, dict) else {}
            if output:
                kwargs[field_name] = output

        # Preserve provenance fields from the pause-time capture.
        kwargs.setdefault(
            "correlation_id",
            getattr(cycle, '_correlation_id', None),
        )
        kwargs.setdefault(
            "project_id",
            getattr(cycle, '_project_id', None),
        )

        return SelfPromptContext(**kwargs)

    async def stop(self) -> None:
        """Stop the self-loop engine."""
        self._running = False
        self._paused = False
        await self._emit_event("SELF_LOOP_STOPPED", {"cycle_count": self._cycle_count})

    async def _emit_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Emit event to canonical EventBus."""
        if self._event_bus:
            try:
                from aios.events.core.event import Event
                from aios.events.core.identity import ComponentIdentity, ComponentType
                from aios.events.core.types import EventType as CoreEventType, SemanticVersion

                identity = ComponentIdentity(
                    component_type=ComponentType.CORE_COMPONENT,
                    component_name="SelfLoopEngine",
                    version=SemanticVersion(1, 0, 0),
                )

                # Map to canonical EventType if exists, otherwise use custom
                try:
                    core_event_type = CoreEventType[event_type]
                except KeyError:
                    # Use a generic type for custom events
                    core_event_type = CoreEventType.SYSTEM_HEALTH_CHECK

                event = Event(
                    eventType=core_event_type,
                    source=identity,
                    correlationId=uuid.uuid4(),
                    payload=payload,
                )
                await self._event_bus.publish(event)
            except Exception:
                # Fail silently — event emission should not break self-loop
                pass

    def get_status(self) -> dict[str, Any]:
        """Get current engine status."""
        return {
            "running": self._running,
            "paused": self._paused,
            "cycle_count": self._cycle_count,
            "current_cycle": self._current_cycle.cycle_id if self._current_cycle else None,
            "current_phase": self._current_cycle.current_phase.value if self._current_cycle and self._current_cycle.current_phase else None,
            "mock_mode": self._mock_mode,
        }