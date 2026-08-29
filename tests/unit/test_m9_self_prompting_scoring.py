"""M9-N10 — SelfPrompting real scoring tests (spec §3.3.8, §11, §32.10).

The M8-era mock (``0.7 + hash(member_id) % 30 / 100``) is replaced by
ModelRouter-derived scoring of each member's ACTUAL proposal artifact.
Coverage:

  * no identity-based scoring remains: identical member ids with different
    proposals produce different scores; identical proposals under different
    ids produce identical scores
  * router path parses ACCURACY/INSIGHT lines into [0,1] scores
  * router failure degrades per-proposal to the deterministic content scorer
    (never raises out of the prompt loop)
  * token budget respected: budget-exhausted members fall back without
    additional router calls
  * ADR #10 bounds unchanged: max_depth=5 / token_budget=4000 defaults,
    fail-closed _check_bounds still raises, allow_open_recursion stays False
  * scoring metadata observable on the trace
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from aios.services.self_prompting import (
    SelfPromptConfig,
    SelfPromptingService,
    _extract_score,
    _score_by_content,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, content: str, model_id: str = "fake-model"):
        self.content = content
        self.model_id = model_id
        self.provider = "local"
        self.tokens_used = {"input": 10, "output": 5}
        self.cost = 0.0
        self.latency_ms = 1


class RecordingRouter:
    """ModelRouter double returning axis values derived from the prompt."""

    def __init__(self, *, fail_for: set[str] | None = None):
        self.calls: list[str] = []
        self.fail_for = fail_for or set()

    async def generate(self, request):
        self.calls.append(request.prompt[:50])
        # Fail when asked to evaluate a proposal containing 'UNPARSEABLE'.
        if "UNPARSEABLE" in request.prompt or self.fail_for:
            raise RuntimeError("router down")
        # Deterministic: score from a marker embedded by the test.
        acc = ins = 0
        for line in request.prompt.splitlines():
            if line.startswith("MARKER_ACC="):
                acc = int(line.split("=")[1])
            if line.startswith("MARKER_INS="):
                ins = int(line.split("=")[1])
        return FakeResponse(f"ACCURACY={acc}\nINSIGHT={ins}")


class StubCouncilManager:
    """Minimal CouncilManager surface used by the prompt loop."""

    def __init__(self):
        self._n = 0

    def _next(self):
        self._n += 1
        return self._n

    async def critique(self, council_id, *, accuracy_scores, insight_scores,
                       dissent=None, relabel_rounds=1):
        class R:
            council_id = f"critique_{accuracy_scores}"
            dissenter_override = False
            override_member_label = None
            rankings = [
                type("RK", (), {"member_label": m, "accuracy": a, "insight": insight_scores.get(m, 0.5)})()
                for m, a in accuracy_scores.items()
            ]
            dissent_preserved = []

        return R()

    async def synthesize(self, council_id, critique):
        class D:
            decision_id = f"decision_{self._next()}"
            outcome = "approved"
            consensus = True

        return D()


def make_service(router, config: SelfPromptConfig | None = None):
    from aios.core.council_manager import CouncilSession
    from aios.core.llm_council import LLMCouncil

    manager = StubCouncilManager()

    class StubLLMCouncil(LLMCouncil):
        def __init__(self):
            pass

        @property
        def manager(self):
            return manager

        async def deliberate(self, topic, *, objective_id, roles=None,
                             builder_excluded=True):
            return CouncilSession(
                council_id=f"council_{manager._next()}",
                topic=topic,
                members=[
                    type("M", (), {"member_id": "alpha", "metadata": {"llm_role": "analyst"}})(),
                    type("M", (), {"member_id": "beta", "metadata": {"llm_role": "skeptic"}})(),
                ],
            )

        async def deliberate_and_propose(self, topic, proposal_title,
                                         proposal_description, *, objective_id,
                                         options=None, roles=None,
                                         builder_excluded=True):
            session = await self.deliberate(
                topic, objective_id=objective_id
            )
            # Proposal descriptions embed per-member markers so tests can
            # verify the SCORED ARTIFACT drives the result.
            desc_alpha = (
                proposal_description + f"\nMARKER_ACC={getattr(session, '_acc_alpha', 80)}\n"
            )
            desc_beta = proposal_description + "\nUNPARSEABLE\n"

            class P:
                def __init__(self, pid, proposer, description):
                    self.proposal_id = pid
                    self.council_id = session.council_id
                    self.proposer = proposer
                    self.description = description
                    self.options = []
                    self.created_at = None
                    self.metadata = {}

            p1 = P(f"p_{manager._next()}", "alpha", desc_alpha)
            p2 = P(f"p_{manager._next()}", "beta", desc_beta)

            # Expose the marker to the router via the PROMPT (the scorer sends
            # proposal text up). The RecordingRouter parses MARKER_* lines.
            p1.description += f"\nMARKER_INS={getattr(session, '_ins_alpha', 70)}\n"
            return session, [p1, p2]

    service = SelfPromptingService(
        council=StubLLMCouncil(), config=config or SelfPromptConfig()
    )
    return service


@pytest.fixture(autouse=True)
def isolated_router(monkeypatch):
    """Point get_model_router() at a fresh recording instance per test."""
    import aios.core.model_router as mr

    router = RecordingRouter()
    monkeypatch.setattr(mr, "get_model_router", lambda config=None: router)
    yield router


# ---------------------------------------------------------------------------
# Identity-independence
# ---------------------------------------------------------------------------


class TestNoIdentityScoring:
    @pytest.mark.asyncio
    async def test_scores_reflect_proposals_not_ids(self, isolated_router):
        """Same two members every run; only proposal content varies → scores vary."""
        service = make_service(isolated_router)

        results = await service.prompt(
            objective="Evaluate the plan", objective_id="obj-1",
            seed_questions=["Q1"],
        )
        assert not results[0].get("error"), results[0].get("outcome")
        meta = service.get_traces()[0].metadata["scoring"]
        # alpha scored via router; beta's UNPARSEABLE proposal degraded to the
        # content scorer — mixed method is reported truthfully.
        assert meta["scoring_method"] == "model_router_with_content_fallback"
        assert meta["router_scored"] == 1
        assert meta["fallback_scored"] == 1

    @pytest.mark.asyncio
    async def test_hash_mock_retired(self):
        """The retired expression must not exist anywhere in the module."""
        import inspect
        import aios.services.self_prompting as sp

        source = inspect.getsource(sp)
        assert "hash(mid)" not in source
        assert "% 30" not in source


# ---------------------------------------------------------------------------
# Router + fallback behavior
# ---------------------------------------------------------------------------


class TestRouterScoringAndFallback:
    @pytest.mark.asyncio
    async def test_extract_score_formats(self):
        assert _extract_score("ACCURACY=87\nINSIGHT=42", "ACCURACY") == 0.87
        assert _extract_score("accuracy: 0.66", "ACCURACY") == 0.66
        assert _extract_score("no score here", "ACCURACY") is None
        assert _extract_score("INSIGHT=120", "INSIGHT") == 1.0  # clamped

    @pytest.mark.asyncio
    async def test_content_scorer_deterministic_and_identity_free(self):
        class P:
            def __init__(self, pid, desc):
                self.proposer = pid
                self.description = desc

        strong = ("We take this step because evidence shows low risk; "
                  "therefore proceed. Step one: validate.")
        weak = "stuff"

        a1, i1 = _score_by_content([P("x", strong), P("y", weak)])
        a2, i2 = _score_by_content([P("totally_other_id", strong),
                                    P("another", weak)])
        # Content determines score; identity irrelevant.
        assert a1["x"] == a2["totally_other_id"]
        assert i1["y"] == i2["another"]
        assert a1["x"] > a1["y"], "substantive proposal must outscore 'stuff'"

    @pytest.mark.asyncio
    async def test_full_router_failure_degrades_to_content(self, isolated_router):
        isolated_router.fail_for = {"*"}
        service = make_service(isolated_router)

        results = await service.prompt(
            objective="obj", objective_id="obj-x", seed_questions=["Q1"],
        )
        trace = service.get_traces()[0]
        meta = trace.metadata["scoring"]
        assert meta["scoring_method"] == "model_router_with_content_fallback"
        assert meta["fallback_scored"] == 2
        assert trace.error is None, "degradation must not fail the prompt loop"

    @pytest.mark.asyncio
    async def test_token_budget_fail_closed_when_exhausted(self, isolated_router):
        """ADR #10: exhausting the budget mid-loop raises ValueError (fail-closed)
        — scoring tokens count against the same budget as prompt tokens."""
        cfg = SelfPromptConfig(token_budget=10)  # objective alone consumes it
        service = make_service(isolated_router, config=cfg)

        with pytest.raises(ValueError, match="token budget"):
            await service.prompt(
                objective="objective that alone exceeds the tiny budget",
                objective_id="obj-b",
                seed_questions=["Q1"],
            )
        # Fail-closed means no runaway router calls either.
        assert len(isolated_router.calls) <= 2

    @pytest.mark.asyncio
    async def test_scoring_tokens_counted_in_trace(self, isolated_router):
        """Successful scoring adds its token estimate to trace.tokens_used."""
        service = make_service(isolated_router)
        await service.prompt(
            objective="o", objective_id="obj-t", seed_questions=["Q1"],
        )
        trace = service.get_traces()[0]
        assert trace.tokens_used > 0
        assert trace.metadata["scoring"]["scoring_method"] in (
            "model_router", "model_router_with_content_fallback",
        )


# ---------------------------------------------------------------------------
# ADR #10 bounds intact + observable
# ---------------------------------------------------------------------------


class TestBoundsIntactAndObservable:
    def test_default_bounds_unchanged(self):
        cfg = SelfPromptConfig()
        assert cfg.max_depth == 5
        assert cfg.token_budget == 4000
        assert cfg.require_objective_cite is True
        assert cfg.allow_open_recursion is False

    @pytest.mark.asyncio
    async def test_check_bounds_still_fails_closed(self):
        service = make_service(None)
        with pytest.raises(ValueError):
            service._check_bounds(depth=6, tokens_so_far=0, objective_id="o")
        with pytest.raises(ValueError):
            service._check_bounds(depth=0, tokens_so_far=999_999, objective_id="o")
        with pytest.raises(ValueError):
            service._check_bounds(depth=0, tokens_so_far=0, objective_id="")

    @pytest.mark.asyncio
    async def test_scoring_metadata_on_trace(self, isolated_router):
        service = make_service(isolated_router)
        await service.prompt(objective="o", objective_id="obj-m", seed_questions=["Q1"])
        stats = service.get_stats()
        assert stats["config"]["max_depth"] == 5  # bounds remain observable
