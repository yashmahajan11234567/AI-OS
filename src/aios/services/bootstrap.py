"""M9-N1 — Engineering-service bootstrap (GAP-A closure).

Instantiates and registers every Engineering Service into the canonical C2
``ServiceRegistry`` under the reserved ``engineering.<name>`` namespace, in
dependency order, so that the kernel's existing start loop
(``kernel.py::_start_services``) can start them. Prior to M9 no bootstrap
existed: the services were defined but never wired into a running kernel, so
``LearningService.on_start`` never ran, the ``RootCauseAnalyzer`` was never
constructed by the kernel, and the M7 closed loop stayed silent (spec §2
GAP-A).

Design constraints (M9-IMPLEMENTATION-SPEC §11.1, §13, §19):

* Idempotent — re-running replaces existing instances (unregister-then-
  re-register; the canonical registry rejects duplicate ids per SR-REG-001).
* Importable & callable without a live kernel — accepts an injected registry;
  when omitted, the legacy-compatible wrapper delegating to the canonical C2
  singleton is used.
* Honors dependency order — ``memory`` before ``planning``/``learning``/
  ``coding``, ``planning`` before ``coding``, ``coding`` before ``review``,
  ``review`` before ``deployment``, ``deployment`` before ``operations``.
  (``review`` additionally names ``ai_agency`` and ``deployment`` names
  ``testing`` in their ``depends_on`` facets; those roles are fulfilled by
  the kernel-owned agency adapters and the M7 ``TestOrchestratorService``
  respectively and have no stand-alone BaseService to register here.)
* Partial-failure tolerant — a failing service is logged and skipped; the
  remaining services still bootstrap (R-8 mitigation, mirrors the per-service
  try/except of the kernel start loop).
* Optional ``services.enabled`` allowlist (spec §19) — empty/absent means all
  engineering services are enabled (bootstrap on by default in a full kernel).
* Populates the kernel-bound singletons the rest of M9 depends on:
  ``set_learning_service_instance`` (eagerly, so GAP-B retrieval and the
  RCA→Learning handoff work even before ``start()``),
  ``set_self_prompting_service``, the ``RootCauseAnalyzer`` module global,
  and — per spec §22 — the M7 ``TestOrchestratorService`` closed-loop
  collaborators (``_learning`` / ``_planning`` / ``_rca``), which the kernel
  constructs without them because ``_init_m7_testing`` runs before any
  engineering service exists. The M7 file itself stays frozen; the wiring is
  done from here, on the M9 side of the boundary.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from aios.services.base import BaseService
from aios.services.registry import ServiceRegistry

logger = logging.getLogger(__name__)

#: Ordered (name, factory) pairs. Order IS the dependency order — the legacy
#: wrapper records no canonical ``depends_on``, so ordering is enforced here.
#: Keep new services inserted after their dependencies.
_SERVICE_FACTORIES: list[tuple[str, Callable[[], BaseService]]] = [
    ("memory", lambda: _lazy("aios.services.memory", "MemoryService")),
    ("planning", lambda: _lazy("aios.services.planning", "PlanningService")),
    ("learning", lambda: _lazy("aios.services.learning", "LearningService")),
    ("coding", lambda: _lazy("aios.services.coding", "CodingService")),
    ("review", lambda: _lazy("aios.services.review", "ReviewService")),
    ("deployment", lambda: _lazy("aios.services.deployment", "DeploymentService")),
    ("operations", lambda: _lazy("aios.services.operations", "OperationsService")),
    ("mcp", lambda: _lazy("aios.services.mcp", "MCPService")),
    ("skill", lambda: _lazy("aios.services.skill", "SkillService")),
    ("council", lambda: _lazy("aios.services.council", "CouncilService")),
    (
        "self_prompting",
        lambda: _lazy("aios.services.self_prompting", "SelfPromptingService"),
    ),
]


def _lazy(module_name: str, class_name: str) -> BaseService:
    """Instantiate a service class, importing its module on first use.

    Deferred imports keep ``import aios.services.bootstrap`` cheap and free of
    manager-singleton side effects until bootstrap actually runs.
    """
    import importlib

    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return cls()


def bootstrap_engineering_services(
    *,
    registry: ServiceRegistry | None = None,
    enabled: list[str] | None = None,
    kernel: Any | None = None,
) -> list[BaseService]:
    """Instantiate + register all engineering services (spec §11.1).

    Args:
        registry: Legacy-compatible ``ServiceRegistry`` wrapper targeting the
            canonical C2 registry. When ``None`` a fresh wrapper over the
            canonical singleton is used.
        enabled: Optional allowlist of service names (``services.enabled``,
            spec §19). ``None`` or empty enables everything.
        kernel: Optional running ``HermesKernel``; when supplied, the M7
            ``TestOrchestratorService`` closed-loop collaborators are
            back-filled (spec §22).

    Returns:
        The list of services successfully instantiated and registered, in
        dependency order. Construction/registration failures are logged and
        skipped (partial bootstrap, R-8).
    """
    target = registry if registry is not None else ServiceRegistry()
    enabled_set = (
        {str(name).strip().lower() for name in enabled} if enabled else None
    )

    instantiated: list[BaseService] = []
    for name, factory in _SERVICE_FACTORIES:
        if enabled_set is not None and name not in enabled_set:
            logger.debug("Bootstrap: service '%s' disabled by allowlist", name)
            continue
        try:
            service = factory()
        except Exception as exc:  # noqa: BLE001 — partial-bootstrap isolation (R-8)
            logger.error("Bootstrap: failed to construct service '%s': %s", name, exc)
            continue
        try:
            # Idempotent replacement (spec §13): the canonical registry rejects
            # duplicate ids (SR-REG-001), so drop any prior registration first.
            # Unregister refuses only when dependents remain; engineering
            # services carry no canonical depends_on, so this cannot happen.
            target.unregister(name)
            target.register(service)
        except Exception as exc:  # noqa: BLE001 — partial-bootstrap isolation (R-8)
            logger.error("Bootstrap: failed to register service '%s': %s", name, exc)
            continue
        instantiated.append(service)
        logger.debug("Bootstrap: registered service '%s'", name)

    _bind_module_globals(instantiated)

    if kernel is not None:
        _wire_kernel_test_loop(kernel, instantiated)

    logger.info(
        "Bootstrap: %d engineering service(s) registered [%s]",
        len(instantiated),
        ", ".join(svc.name for svc in instantiated),
    )
    return instantiated


def _bind_module_globals(instantiated: list[BaseService]) -> None:
    """Eagerly bind the module-level singletons M9 nodes rely on.

    ``LearningService.on_start`` re-binds the learning global when started;
    binding here too means GAP-B retrieval (N2), the planning ingest (N3) and
    the RCA handoff (N4) resolve the bootstrap-created instance even if an
    individual service fails to start.
    """
    from aios.core.root_cause import get_root_cause_analyzer
    from aios.services.learning import set_learning_service_instance
    from aios.services.self_prompting import set_self_prompting_service

    for service in instantiated:
        if service.name == "learning":
            set_learning_service_instance(service)  # type: ignore[arg-type]
        elif service.name == "self_prompting":
            set_self_prompting_service(service)  # type: ignore[arg-type]

    # The RootCauseAnalyzer participates in the closed loop alongside the
    # learning service (FAIL → RCA → Learning); construct/bind it whenever
    # learning is bootstrapped. Module-global singleton: returns the existing
    # instance when already present, so repeated boots stay idempotent.
    if any(svc.name == "learning" for svc in instantiated):
        get_root_cause_analyzer()


def _wire_kernel_test_loop(kernel: Any, instantiated: list[BaseService]) -> None:
    """Back-fill the M7 ``TestOrchestratorService`` closed-loop collaborators.

    Spec §22: the kernel constructs ``TestOrchestratorService`` in
    ``_init_m7_testing`` — before any engineering service exists — leaving
    ``_learning`` / ``_planning`` / ``_rca`` unset, which kept the M7 closed
    loop silent in a real kernel (GAP-A consequence). M9 populates them here
    from the bootstrap-created instances. The M7 source stays frozen; only
    these three optional collaborator slots are filled, and only when still
    empty (an explicit injection always wins).
    """
    orchestrator = getattr(kernel, "_test_orchestrator", None)
    if orchestrator is None:
        return

    def _pick(name: str) -> BaseService | None:
        for service in instantiated:
            if service.name == name:
                return service
        return None

    learning = _pick("learning")
    planning = _pick("planning")
    if learning is not None and getattr(orchestrator, "_learning", None) is None:
        orchestrator._learning = learning
    if planning is not None and getattr(orchestrator, "_planning", None) is None:
        orchestrator._planning = planning
    if learning is not None:
        # RCA rides on the learning slot: the analyzer global is bound whenever
        # learning bootstraps (see _bind_module_globals).
        from aios.core.root_cause import get_root_cause_analyzer

        if getattr(orchestrator, "_rca", None) is None:
            orchestrator._rca = get_root_cause_analyzer()


__all__ = [
    "bootstrap_engineering_services",
]
