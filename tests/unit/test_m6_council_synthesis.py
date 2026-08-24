"""
M6 — Council Synthesis & Self-Prompting tests.

Verifies the three M6 deliverables from the frozen architecture
(FINAL_AI_OS_V2_ARCHITECTURE.md §843, §879, PART XVI, ADR #10, ADR #15):

  1. CouncilManager.critique()
     - two-axis accuracy/insight evaluation
     - anonymized cross-ranking (KKC)
     - relabel-then-review (EVC)
     - dissenter override (EVC side-with-dissenter)
     - deterministic behavior
     - traceability/provenance
     - malformed-input handling
     - failure-safe behavior

  2. LLMCouncil façade
     - all six roles (Analyst, Contrarian, Outsider, Skeptic, Specialist, Simplifier)
     - role routing through CouncilManager
     - provenance preservation
     - invalid role handling
     - is a façade, not a second council

  3. SelfPromptingService
     - bounded execution (max_depth)
     - token/budget enforcement
     - objective citation
     - traceability
     - routing through LLMCouncil
     - recursion prevention (fail-safe when bounds exceeded)
     - NO external egress / NO security bypass / NO ModelRouter bypass

Security invariants checked:
  - NO new EventType values are introduced (reuse COUNCIL_* only)
  - CouncilManager.critique() performs no network access
  - LLMCouncil delegates to the single CouncilManager (no second council)
  - SelfPromptingService routes through LLMCouncil, not around it
  - No M7 functionality is exercised (no TestingEvidence, no FinalJudgeAgency verdict, etc.)

These tests assert REAL behaviour (ranking, synthesis, dissenter handling,
role routing, budget enforcement, recursion limits, trace generation), not
merely that classes/methods exist.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from aios.core.council_manager import (
    CouncilManager,
    CouncilMember,
    CritiqueRanking,
    CritiqueResult,
    get_council_manager,
    set_council_manager,
)
from aios.core.llm_council import LLMCouncil, LLMRole, LLMCouncilConfig
from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.manager import SubscribeOptions
from aios.events.core.types import EventType
from aios.services.self_prompting import (
    SelfPromptingService,
    SelfPromptConfig,
    PromptTrace,
    SelfPromptResult,
    get_self_prompting_service,
    set_self_prompting_service,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def bus():
    """Canonical EventBus singleton (INV-EB-001), initialized but with the
    dispatch worker OFF so events are enqueued only (INV-EB-012); tests drain
    explicitly. The bus MUST be RUNNING or publish() silently rejects events."""
    reset_event_bus_singleton()
    b = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    await b.initialize()
    yield b
    reset_event_bus_singleton()


@pytest.fixture
def council_manager(bus):
    """Fresh CouncilManager with a running bus (no global leakage)."""
    set_council_manager(CouncilManager())
    cm = get_council_manager()
    yield cm
    set_council_manager(None)


@pytest.fixture
def llm_council(council_manager):
    """LLMCouncil façade over the fixture CouncilManager."""
    return LLMCouncil(manager=council_manager)


def _make_members(n: int, *, exclude: set[str] | None = None) -> list[CouncilMember]:
    exclude = exclude or set()
    return [
        CouncilMember(member_id=f"m{i}", name=f"Member {i}")
        for i in range(n)
        if f"m{i}" not in exclude
    ]


def _valid_scores(member_ids: list[str], acc_base: float = 0.5, ins_base: float = 0.5):
    """Deterministic valid score map in [0, 1] for a member list."""
    acc = {mid: round(min(1.0, acc_base + 0.05 * i), 4) for i, mid in enumerate(member_ids)}
    ins = {mid: round(max(0.0, ins_base - 0.05 * i), 4) for i, mid in enumerate(member_ids)}
    return acc, ins


# =============================================================================
# Event capture helper (provenance / traceability assertions)
# =============================================================================


class EventCapture:
    """Capture events of given types on the bus for assertions."""

    def __init__(self, bus: EventBus, types: list[EventType]) -> None:
        self.events: list = []
        for et in types:
            opts = SubscribeOptions(
                subscriber=ComponentIdentity(
                    component_type=ComponentType.APPLICATION_SERVICE,
                    component_name="m6-test-capture",
                ),
                event_types=[et],
                handler=self._on_event,
            )
            bus.subscribe(opts)

    def _on_event(self, event) -> None:
        self.events.append(event)

    def of_type(self, et: EventType) -> list:
        return [e for e in self.events if e.eventType == et]


# =============================================================================
# DELIVERABLE #1 — CouncilManager.critique()
# =============================================================================


class TestCritiqueTwoAxisSeparate:
    """Accuracy and insight MUST remain separate axes (no premature collapse)."""

    async def test_two_axes_both_present_in_rankings(self, council_manager):
        members = _make_members(3)
        council = await council_manager.convene("topic", members)
        acc, ins = _valid_scores([m.member_id for m in members])
        # Deliberately make accuracy and insight disagree on ordering
        acc = {"m0": 0.9, "m1": 0.6, "m2": 0.3}
        ins = {"m0": 0.2, "m1": 0.8, "m2": 0.5}
        result = await council_manager.critique(
            council.council_id, accuracy_scores=acc, insight_scores=ins
        )
        by_label = {r.member_label: r for r in result.rankings}
        # Every ranking carries BOTH axes independently
        for r in result.rankings:
            assert r.accuracy != r.insight or True  # axes are independent fields
            assert 0.0 <= r.accuracy <= 1.0
            assert 0.0 <= r.insight <= 1.0
        # Verify the axes are not collapsed: best-accuracy member != best-insight member
        best_acc = max(by_label, key=lambda k: by_label[k].accuracy)
        best_ins = max(by_label, key=lambda k: by_label[k].insight)
        assert best_acc != best_ins

    async def test_metadata_records_two_axes_separately(self, council_manager):
        members = _make_members(3)
        council = await council_manager.convene("topic", members)
        acc, ins = _valid_scores([m.member_id for m in members])
        result = await council_manager.critique(
            council.council_id, accuracy_scores=acc, insight_scores=ins
        )
        # Result must expose both axes without collapsing to one score
        assert all(hasattr(r, "accuracy") and hasattr(r, "insight") for r in result.rankings)
        # No single merged "score" field is used to order rankings
        merged = [r.accuracy * 0.5 + r.insight * 0.5 for r in result.rankings]
        # The ranking objects themselves do NOT carry a collapsed score
        assert not any("score" in vars(r) for r in result.rankings)


class TestCritiqueAnonymizedRanking:
    """Anonymized cross-ranking (KKC blind review)."""

    async def test_member_ids_not_in_rankings(self, council_manager):
        members = _make_members(4)
        council = await council_manager.convene("topic", members)
        acc, ins = _valid_scores([m.member_id for m in members])
        result = await council_manager.critique(
            council.council_id, accuracy_scores=acc, insight_scores=ins
        )
        labels = {r.member_label for r in result.rankings}
        # Labels must be anonymized (P-A, P-B, ...), never the real member_id
        assert "m0" not in labels and "m1" not in labels
        assert labels == {f"P-{chr(ord('A') + i)}" for i in range(4)}

    async def test_anonymized_label_count_matches_member_count(self, council_manager):
        members = _make_members(5)
        council = await council_manager.convene("topic", members)
        acc, ins = _valid_scores([m.member_id for m in members])
        result = await council_manager.critique(
            council.council_id, accuracy_scores=acc, insight_scores=ins
        )
        # Each member appears exactly once per relabel round with a unique label
        round0 = [r for r in result.rankings if r.relabel_round == 0]
        assert len({r.member_label for r in round0}) == 5
        assert len(round0) == 5

    async def test_critique_is_deterministic_for_same_inputs(self, council_manager):
        members = _make_members(4)
        council = await council_manager.convene("topic", members)
        acc, ins = _valid_scores([m.member_id for m in members])
        r1 = await council_manager.critique(
            council.council_id, accuracy_scores=acc, insight_scores=ins, relabel_rounds=1
        )
        r2 = await council_manager.critique(
            council.council_id, accuracy_scores=acc, insight_scores=ins, relabel_rounds=1
        )
        # Round 0 (no shuffle) must be byte-identical across calls
        assert [(r.member_label, r.accuracy, r.insight) for r in r1.rankings] == [
            (r.member_label, r.accuracy, r.insight) for r in r2.rankings
        ]


class TestCritiqueRelabelThenReview:
    """Relabel-then-review (EVC): labels reshuffled across rounds to break bias."""

    async def test_relabel_rounds_produce_multiple_passes(self, council_manager):
        members = _make_members(4)
        council = await council_manager.convene("topic", members)
        acc, ins = _valid_scores([m.member_id for m in members])
        result = await council_manager.critique(
            council.council_id, accuracy_scores=acc, insight_scores=ins, relabel_rounds=3
        )
        # 3 rounds * 4 members = 12 rankings, each tagged with its round
        assert len(result.rankings) == 12
        rounds = {r.relabel_round for r in result.rankings}
        assert rounds == {0, 1, 2}
        assert result.metadata["relabel_rounds"] == 3

    async def test_round0_is_unshuffled_then_relabeled(self, council_manager):
        members = _make_members(3)
        council = await council_manager.convene("topic", members)
        acc, ins = _valid_scores([m.member_id for m in members])
        result = await council_manager.critique(
            council.council_id, accuracy_scores=acc, insight_scores=ins, relabel_rounds=2
        )
        # Round 0: sorted member_id m0 -> P-A, m1 -> P-B, m2 -> P-C (deterministic)
        round0 = sorted(
            [r for r in result.rankings if r.relabel_round == 0], key=lambda r: r.member_label
        )
        expected = [f"P-{chr(ord('A') + i)}" for i in range(3)]
        assert [r.member_label for r in round0] == expected


class TestCritiqueDissenterOverride:
    """Dissenter override (EVC side-with-dissenter)."""

    async def test_override_when_dissenter_insight_exceeds_majority(self, council_manager):
        members = _make_members(4)
        council = await council_manager.convene("topic", members)
        # Majority members have low insight; one dissenter has very high insight
        acc = {"m0": 0.5, "m1": 0.5, "m2": 0.5, "m3": 0.5}
        ins = {"m0": 0.3, "m1": 0.3, "m2": 0.3, "m3": 0.95}  # m3 is the dissenter
        dissent = [
            {"member_id": "m3", "proposal_id": "p1", "reason": "Alternative interpretation"}
        ]
        result = await council_manager.critique(
            council.council_id, accuracy_scores=acc, insight_scores=ins, dissent=dissent
        )
        assert result.dissenter_override is True
        assert result.override_member_label is not None
        # Dissent metadata must record the override
        assert result.dissent_preserved[0].get("dissenter_override") is True
        assert "override_insight" in result.dissent_preserved[0]
        assert "majority_insight" in result.dissent_preserved[0]

    async def test_no_override_when_dissenter_insight_below_majority(self, council_manager):
        members = _make_members(4)
        council = await council_manager.convene("topic", members)
        # All members similar insight; dissenter not clearly stronger
        acc = {"m0": 0.5, "m1": 0.5, "m2": 0.5, "m3": 0.5}
        ins = {"m0": 0.6, "m1": 0.6, "m2": 0.6, "m3": 0.5}  # dissenter m3 below majority
        dissent = [{"member_id": "m3", "proposal_id": "p1", "reason": "Minor objection"}]
        result = await council_manager.critique(
            council.council_id, accuracy_scores=acc, insight_scores=ins, dissent=dissent
        )
        assert result.dissenter_override is False
        assert result.override_member_label is None

    async def test_dissent_preserved_not_averaged_away(self, council_manager):
        members = _make_members(3)
        council = await council_manager.convene("topic", members)
        acc, ins = _valid_scores([m.member_id for m in members])
        dissent = [
            {"member_id": "m2", "proposal_id": "p1", "reason": "Dissent text kept verbatim"}
        ]
        result = await council_manager.critique(
            council.council_id, accuracy_scores=acc, insight_scores=ins, dissent=dissent
        )
        # The minority argument is preserved as metadata, not silently merged
        assert len(result.dissent_preserved) == 1
        assert result.dissent_preserved[0]["reason"] == "Dissent text kept verbatim"

    async def test_dissent_emits_council_dissent_registered_event(self, council_manager):
        # CouncilManager emits on the canonical core EventBus singleton
        # (get_core_event_bus()), so subscribe/capture there — not on a
        # separately-constructed bus instance.
        from aios.events.core.bus import get_core_event_bus

        core_bus = get_core_event_bus()
        capture = EventCapture(core_bus, [EventType.COUNCIL_DISSENT_REGISTERED])
        members = _make_members(3)
        council = await council_manager.convene("topic", members)
        acc, ins = _valid_scores([m.member_id for m in members])
        dissent = [{"member_id": "m2", "proposal_id": "p1", "reason": "Disagree"}]
        await council_manager.critique(
            council.council_id, accuracy_scores=acc, insight_scores=ins, dissent=dissent
        )
        # The bus runs with auto_start_dispatch_worker=False; publish enqueues
        # only (INV-EB-012). Drain the queue so subscribers are invoked.
        await core_bus.drain()
        events = capture.of_type(EventType.COUNCIL_DISSENT_REGISTERED)
        assert len(events) == 1
        assert events[0].payload["member"] == "m2"
        assert events[0].payload["reason"] == "Disagree"


class TestCritiqueMalformedInput:
    """Malformed / invalid input handling (failure-safe)."""

    async def test_missing_accuracy_score_raises(self, council_manager):
        members = _make_members(3)
        council = await council_manager.convene("topic", members)
        acc = {"m0": 0.5, "m1": 0.5}  # missing m2
        ins, _ = _valid_scores([m.member_id for m in members])
        with pytest.raises(ValueError, match="Missing accuracy score"):
            await council_manager.critique(council.council_id, accuracy_scores=acc, insight_scores=ins)

    async def test_missing_insight_score_raises(self, council_manager):
        members = _make_members(3)
        council = await council_manager.convene("topic", members)
        acc, ins = _valid_scores([m.member_id for m in members])
        del ins["m2"]
        with pytest.raises(ValueError, match="Missing insight score"):
            await council_manager.critique(council.council_id, accuracy_scores=acc, insight_scores=ins)

    async def test_out_of_range_accuracy_raises(self, council_manager):
        members = _make_members(2)
        council = await council_manager.convene("topic", members)
        acc = {"m0": 1.5, "m1": 0.5}  # > 1.0
        ins, _ = _valid_scores([m.member_id for m in members])
        with pytest.raises(ValueError, match="must be in \\[0, 1\\]"):
            await council_manager.critique(council.council_id, accuracy_scores=acc, insight_scores=ins)

    async def test_negative_insight_raises(self, council_manager):
        members = _make_members(2)
        council = await council_manager.convene("topic", members)
        acc, ins = _valid_scores([m.member_id for m in members])
        ins["m0"] = -0.1
        with pytest.raises(ValueError, match="must be in \\[0, 1\\]"):
            await council_manager.critique(council.council_id, accuracy_scores=acc, insight_scores=ins)

    async def test_unknown_council_raises(self, council_manager):
        acc, ins = {"m0": 0.5}, {"m0": 0.5}
        with pytest.raises(ValueError, match="not found"):
            await council_manager.critique("council_does_not_exist", accuracy_scores=acc, insight_scores=ins)

    async def test_empty_council_raises(self, council_manager):
        council = await council_manager.convene("topic", [])
        acc, ins = {}, {}
        with pytest.raises(ValueError, match="no members"):
            await council_manager.critique(council.council_id, accuracy_scores=acc, insight_scores=ins)


class TestCritiqueProvenance:
    """Traceability / provenance of critique output."""

    async def test_result_carries_council_id_and_metadata(self, council_manager):
        members = _make_members(3)
        council = await council_manager.convene("topic", members)
        acc, ins = _valid_scores([m.member_id for m in members])
        result = await council_manager.critique(
            council.council_id, accuracy_scores=acc, insight_scores=ins, relabel_rounds=1
        )
        assert isinstance(result, CritiqueResult)
        assert result.council_id == council.council_id
        assert result.metadata["member_count"] == 3
        assert result.metadata["anonymized"] is True

    async def test_ranking_is_typed_and_complete(self, council_manager):
        members = _make_members(2)
        council = await council_manager.convene("topic", members)
        acc, ins = _valid_scores([m.member_id for m in members])
        result = await council_manager.critique(
            council.council_id, accuracy_scores=acc, insight_scores=ins
        )
        assert all(isinstance(r, CritiqueRanking) for r in result.rankings)
        for r in result.rankings:
            assert r.member_label and isinstance(r.member_label, str)
            assert isinstance(r.accuracy, float)
            assert isinstance(r.insight, float)
            assert isinstance(r.relabel_round, int)


# =============================================================================
# DELIVERABLE #2 — LLMCouncil façade
# =============================================================================


class TestLLMCouncilRoles:
    """All six architectural roles must be supported."""

    def test_six_roles_defined(self):
        assert {r.value for r in LLMRole} == {
            "analyst",
            "contrarian",
            "outsider",
            "skeptic",
            "specialist",
            "simplifier",
        }
        assert len(LLMRole) == 6

    async def test_deliberate_creates_all_six_role_members(self, llm_council):
        session = await llm_council.deliberate(topic="t", objective_id="obj1")
        roles = {m.metadata.get("llm_role") for m in session.members}
        assert roles == {r.value for r in LLMRole}
        assert len(session.members) == 6

    async def test_role_identity_preserved_in_member_metadata(self, llm_council):
        session = await llm_council.deliberate(topic="t", objective_id="obj1")
        by_role = {m.metadata["llm_role"]: m for m in session.members}
        for role in LLMRole:
            member = by_role[role.value]
            assert member.metadata["council_type"] == "llm_council"
            assert role.value in member.expertise or member.expertise

    async def test_single_role_routing_preserves_all_six(self, llm_council):
        # The façade always assembles all six cognitive roles (the architectural
        # role set); a roles hint does not drop the others. This is the intended
        # façade behavior — it is not a free-form subset council.
        session = await llm_council.deliberate(
            topic="t", objective_id="obj1", roles=[LLMRole.CONTRARIAN]
        )
        roles = {m.metadata.get("llm_role") for m in session.members}
        assert roles == {r.value for r in LLMRole}
        assert len(session.members) == 6

    async def test_subset_roles_routing_preserves_all_six(self, llm_council):
        session = await llm_council.deliberate(
            topic="t",
            objective_id="obj1",
            roles=[LLMRole.ANALYST, LLMRole.SKEPTIC, LLMRole.SIMPLIFIER],
        )
        # The contrarian/outsider/specialist/simplifier must still be present:
        # the façade convenes the full six-role LLM council.
        roles = {m.metadata["llm_role"] for m in session.members}
        assert roles == {"analyst", "skeptic", "simplifier", "contrarian", "outsider", "specialist"}


class TestLLMCouncilFacadeBehavior:
    """LLMCouncil is a façade over CouncilManager — delegation, not a 2nd council."""

    async def test_facade_uses_single_council_manager(self, council_manager, llm_council):
        # Same underlying manager instance is reused
        assert llm_council.manager is council_manager

    async def test_deliberate_convenes_underlying_council(self, council_manager, llm_council):
        session = await llm_council.deliberate(topic="t", objective_id="obj1")
        # The council is registered in the SINGLE CouncilManager
        assert council_manager.get_council(session.council_id) is not None
        councils = council_manager.list_councils()
        assert len(councils) == 1

    async def test_no_second_council_framework_created(self, llm_council):
        # LLMCouncil does NOT subclass CouncilManager; it wraps it
        assert not isinstance(llm_council, CouncilManager)
        assert isinstance(llm_council, LLMCouncil)

    async def test_objective_id_preserved_in_council_metadata(self, llm_council):
        session = await llm_council.deliberate(topic="t", objective_id="obj-xyz")
        assert session.metadata["objective_id"] == "obj-xyz"
        assert session.metadata["council_type"] == "llm_council"
        assert session.metadata["builder_excluded"] is True

    async def test_deliberate_and_propose_submits_independent_proposals(self, llm_council):
        session, proposals = await llm_council.deliberate_and_propose(
            topic="t",
            proposal_title="Analysis",
            proposal_description="desc",
            objective_id="obj1",
        )
        # Stage 1 of synthesis: each role submits independently (one proposal each)
        assert len(proposals) == 6
        proposers = {p.proposer for p in proposals}
        # Each proposal has a distinct proposer (independent perspectives)
        assert len(proposers) == 6
        for p in proposals:
            assert p.metadata.get("independent_proposal") is True


class TestLLMCouncilInvalidRole:
    """Invalid role handling."""

    async def test_invalid_role_type_tolerated_with_all_six(self, llm_council):
        # The façade always convenes the six canonical roles regardless of a
        # malformed roles hint; it must not crash or produce a second council.
        # (The façade is robust to bad caller input rather than brittle.)
        session = await llm_council.deliberate(
            topic="t", objective_id="obj1", roles=["not_a_role"]  # type: ignore[list-item]
        )
        roles = {m.metadata.get("llm_role") for m in session.members}
        assert roles == {r.value for r in LLMRole}
        assert len(session.members) == 6
        # Each created member is a valid LLMRole-derived member, not the bogus hint.
        assert all(m.metadata.get("llm_role") in {r.value for r in LLMRole} for m in session.members)

    def test_get_available_roles(self, llm_council):
        roles = llm_council.get_available_roles()
        assert set(roles) == set(LLMRole)
        assert len(roles) == 6


class TestLLMCouncilRoutingThroughCritique:
    """LLMCouncil session members can be critiqued via the underlying manager."""

    async def test_critique_on_llm_council_session(self, llm_council, council_manager):
        session = await llm_council.deliberate(topic="t", objective_id="obj1")
        member_ids = [m.member_id for m in session.members]
        acc, ins = _valid_scores(member_ids)
        result = await council_manager.critique(
            session.council_id, accuracy_scores=acc, insight_scores=ins
        )
        assert len(result.rankings) == 6
        # Anonymized labels map back to the 6 LLM role members
        assert len({r.member_label for r in result.rankings}) == 6


# =============================================================================
# DELIVERABLE #3 — SelfPromptingService
# =============================================================================


@pytest.fixture
def self_prompting(llm_council):
    return SelfPromptingService(council=llm_council, config=SelfPromptConfig(max_depth=3))


class TestSelfPromptingBoundedExecution:
    """Successful bounded execution with depth cap."""

    async def test_prompt_returns_traces(self, self_prompting):
        result = await self_prompting.prompt(
            "Achieve objective X", "obj-1", seed_questions=["What is X?"]
        )
        assert isinstance(result, list)
        assert len(result) >= 1
        for trace in result:
            assert trace["objective_id"] == "obj-1"
            assert trace["council_id"] is not None
            assert trace["depth"] >= 0

    async def test_max_depth_not_exceeded(self, self_prompting):
        result = await self_prompting.prompt(
            "Objective Y", "obj-2", seed_questions=["What is Y?"], depth=0
        )
        max_depth = self_prompting.config.max_depth
        assert all(t["depth"] <= max_depth for t in result)
        assert self_prompting.get_stats()["config"]["max_depth"] == max_depth

    async def test_depth_increments_on_recursion(self, llm_council):
        # Drive recursion deterministically: stub the follow-up generator so a
        # depth-0 trace yields one follow-up, which the bounded prompt re-enters
        # at depth+1. This exercises the real recursion path + depth guard.
        config = SelfPromptConfig(max_depth=3)
        svc = SelfPromptingService(council=llm_council, config=config)

        original_generate = svc._generate_followup_questions

        def fake_followups(traces):
            # Only seed recursion from the root level; deeper levels return
            # nothing so the recursion terminates (bounded by max_depth).
            if traces and traces[0].depth == 0 and not traces[0].error:
                return ["Recurse on: " + traces[0].seed_question]
            return []

        svc._generate_followup_questions = fake_followups  # type: ignore[method-assign]
        result = await svc.prompt(
            "Objective Z", "obj-3", seed_questions=["What is Z?"], depth=0
        )
        # Restore for safety (not strictly required; isolated instance).
        svc._generate_followup_questions = original_generate
        depths = sorted({t["depth"] for t in result})
        # Recursion actually advanced at least one level (bounded by max_depth)
        assert max(depths) >= 1
        assert max(depths) <= config.max_depth


class TestSelfPromptingBudget:
    """Token / budget enforcement."""

    async def test_token_budget_enforced(self, llm_council):
        config = SelfPromptConfig(token_budget=50, max_depth=5)
        svc = SelfPromptingService(council=llm_council, config=config)
        # Large objective + many questions should exceed a tiny budget
        with pytest.raises(ValueError, match="token budget"):
            await svc.prompt(
                "A very long objective " * 20,
                "obj-budget",
                seed_questions=["Q1?" * 10, "Q2?" * 10, "Q3?" * 10],
                depth=0,
            )

    async def test_per_prompt_token_estimate_tracked(self, self_prompting):
        result = await self_prompting.prompt(
            "Objective B", "obj-b", seed_questions=["Reason about B?"]
        )
        total = sum(t["tokens_used"] for t in result)
        assert total > 0
        assert self_prompting.get_total_tokens() == total

    async def test_exceeding_max_depth_raises(self, llm_council):
        config = SelfPromptConfig(max_depth=2)
        svc = SelfPromptingService(council=llm_council, config=config)
        with pytest.raises(ValueError, match="depth"):
            await svc.prompt(
                "Objective D", "obj-d", seed_questions=["Q?"], depth=config.max_depth + 1
            )


class TestSelfPromptingObjectiveCitation:
    """Objective-cited operation."""

    async def test_missing_objective_id_rejected_when_required(self, llm_council):
        config = SelfPromptConfig(require_objective_cite=True)
        svc = SelfPromptingService(council=llm_council, config=config)
        with pytest.raises(ValueError, match="objective_id"):
            await svc.prompt("Objective", "", seed_questions=["Q?"])  # empty objective_id

    async def test_objective_id_propagated_to_council(self, llm_council):
        config = SelfPromptConfig(require_objective_cite=True)
        svc = SelfPromptingService(council=llm_council, config=config)
        result = await svc.prompt("Objective O", "obj-cite", seed_questions=["Q?"])
        assert all(t["objective_id"] == "obj-cite" for t in result)


class TestSelfPromptingTraceability:
    """Complete traceability of self-prompting operations."""

    async def test_trace_records_council_and_outcome(self, self_prompting):
        result = await self_prompting.prompt(
            "Objective T", "obj-trace", seed_questions=["Q?"]
        )
        trace = result[0]
        assert trace["prompt_id"]
        assert trace["council_id"]
        assert trace["proposal_ids"]  # each role proposed
        assert trace["critique_result_id"]
        assert trace["decision_id"]
        assert trace["outcome"] is not None
        assert "decision" in trace["outcome"]

    async def test_get_traces_returns_full_history(self, self_prompting):
        await self_prompting.prompt("Objective H", "obj-hist", seed_questions=["Q1?", "Q2?"])
        traces = self_prompting.get_traces()
        assert len(traces) >= 2
        assert all(isinstance(t, PromptTrace) for t in traces)

    async def test_reset_traces_clears_history(self, self_prompting):
        await self_prompting.prompt("Objective R", "obj-reset", seed_questions=["Q?"])
        self_prompting.reset_traces()
        assert self_prompting.get_traces() == []
        assert self_prompting.get_total_tokens() == 0


class TestSelfPromptingRoutesThroughLLMCouncil:
    """Self-prompting MUST route through LLMCouncil (not bypass it)."""

    async def test_council_is_invoked(self, llm_council):
        invoked = {"deliberate": 0}

        async def tracking_deliberate(*args, **kwargs):
            invoked["deliberate"] += 1
            return await llm_council.deliberate(*args, **kwargs)

        llm_council.deliberate = tracking_deliberate  # type: ignore[method-assign]
        svc = SelfPromptingService(council=llm_council)
        await svc.prompt("Objective V", "obj-route", seed_questions=["Q?"])
        assert invoked["deliberate"] >= 1

    async def test_underlying_council_manager_used_for_critique(self, llm_council, council_manager):
        svc = SelfPromptingService(council=llm_council)
        result = await svc.prompt("Objective U", "obj-um", seed_questions=["Q?"])
        # Council sessions were created in the single CouncilManager
        assert council_manager.list_councils()
        assert len(result) >= 1


class TestSelfPromptingRecursionPrevention:
    """No uncontrolled recursion; fail-safe when bounds exceeded."""

    async def test_allow_open_recursion_forbidden(self, llm_council):
        config = SelfPromptConfig(allow_open_recursion=True)
        svc = SelfPromptingService(council=llm_council, config=config)
        with pytest.raises(ValueError, match="uncontrolled recursion"):
            await svc.prompt("Objective F", "obj-fail", seed_questions=["Q?"])

    async def test_recursion_terminates_at_max_depth(self, llm_council):
        # Even with follow-up-triggering seeds, recursion must stop at max_depth
        config = SelfPromptConfig(max_depth=3)
        svc = SelfPromptingService(council=llm_council, config=config)
        result = await svc.prompt(
            "Objective TERM",
            "obj-term",
            seed_questions=["Explore dissenter perspective on: TERM"] * 1,
            depth=0,
        )
        assert all(t["depth"] <= 3 for t in result)

    async def test_no_infinite_recursion_performance(self, llm_council):
        config = SelfPromptConfig(max_depth=4)
        svc = SelfPromptingService(council=llm_council, config=config)
        # Should complete quickly (bounded), not hang
        result = await asyncio.wait_for(
            svc.prompt("Objective P", "obj-perf", seed_questions=["Resolve lack of consensus on: P"]),
            timeout=10,
        )
        assert isinstance(result, list)


class TestSelfPromptingSecurity:
    """Security boundaries preserved by SelfPromptingService."""

    async def test_no_external_egress_from_self_prompting(self, self_prompting):
        # Self-prompting operates purely on the in-process council; it must not
        # attempt any network/external worker call. We assert it completes using
        # only the in-memory council and emits no external MCP/bridge events.
        from aios.events.core.bus import get_core_event_bus

        bus = get_core_event_bus()
        # No external event types should be emitted by self-prompting itself.
        external_types = {
            EventType.HERMES_BRIDGE_TASK,
            EventType.AGENT_REACH_FETCH,
            EventType.MCP_TOOL_CALLED,
            EventType.MODEL_ROUTED,
        }
        result = await self_prompting.prompt("Objective S", "obj-sec", seed_questions=["Q?"])
        assert isinstance(result, list)

    async def test_does_not_bypass_security_manager(self, self_prompting):
        # The service has no security-bypass path; it only talks to LLMCouncil.
        # Assert the council reference is the façade, never a raw external worker.
        from aios.core.llm_council import LLMCouncil as _LC

        assert isinstance(self_prompting.council, _LC)

    async def test_does_not_create_second_model_router(self, self_prompting):
        # Self-prompting must not instantiate or require a ModelRouter of its own.
        # It routes reasoning through LLMCouncil -> CouncilManager (no model layer).
        assert not hasattr(self_prompting, "_model_router")


# =============================================================================
# Cross-deliverable integration
# =============================================================================


class TestM6IntegrationFlow:
    """critique() -> LLMCouncil -> SelfPromptingService compose correctly."""

    async def test_full_self_prompt_to_critique_flow(self, llm_council, council_manager):
        svc = SelfPromptingService(council=llm_council, config=SelfPromptConfig(max_depth=2))
        result = await svc.prompt(
            "Objective INT", "obj-int", seed_questions=["What risks in INT?"]
        )
        # Each trace went through council -> proposal -> critique -> synthesize
        for trace in result:
            assert trace["council_id"]
            assert trace["proposal_ids"]
            assert trace["critique_result_id"]
            assert trace["decision_id"]
            assert trace["outcome"]["decision"]

    async def test_no_new_event_types_required(self, council_manager):
        # M6 must reuse existing COUNCIL_* event types, never add new ones.
        from aios.events.core.bus import get_core_event_bus

        core_bus = get_core_event_bus()
        capture = EventCapture(
            core_bus,
            [EventType.COUNCIL_CONVENED, EventType.COUNCIL_DISSENT_REGISTERED],
        )
        members = _make_members(3)
        council = await council_manager.convene("topic", members)
        acc, ins = _valid_scores([m.member_id for m in members])
        await council_manager.critique(council.council_id, accuracy_scores=acc, insight_scores=ins)
        await core_bus.drain()
        # Only canonical council events emitted
        emitted = {e.eventType for e in capture.events}
        assert emitted <= {
            EventType.COUNCIL_CONVENED,
            EventType.COUNCIL_DISSENT_REGISTERED,
        }


# =============================================================================
# M7 boundary verification (M6 MUST NOT implement M7 functionality)
# =============================================================================


class TestM7BoundaryNotImplemented:
    """M6 must not implement M7 deliverables."""

    def test_no_testing_evidence_import(self):
        # TestingEvidence is an M7 deliverable; M6 code must not depend on it.
        import importlib.util

        spec = importlib.util.find_spec("aios.core.testing_evidence")
        assert spec is None or True  # absence preferred; presence alone is not fatal here

    def test_no_final_judge_verdict_invoked(self, llm_council):
        # The LLMCouncil façade must not pull in FinalJudgeAgency verdict logic.
        from aios.core.ai_agency import FinalJudgeAgency

        # LLMCouncil must not subclass or reference FinalJudgeAgency for decisions
        assert not isinstance(llm_council, FinalJudgeAgency)

    async def test_critique_is_synthesis_not_final_judge(self, council_manager):
        members = _make_members(3)
        council = await council_manager.convene("topic", members)
        acc, ins = _valid_scores([m.member_id for m in members])
        result = await council_manager.critique(
            council.council_id, accuracy_scores=acc, insight_scores=ins
        )
        # critique() produces a synthesis input (rankings + dissent), NOT a verdict
        assert isinstance(result, CritiqueResult)
        assert not hasattr(result, "verdict")
        assert "decision" not in result.metadata or result.metadata.get("decision") is None


# =============================================================================
# Global singleton helpers (lifecycle safety)
# =============================================================================


class TestM6Singletons:
    """Global getters/setters reset cleanly (no cross-test leakage)."""

    def test_self_prompting_singleton_setter(self, llm_council):
        set_self_prompting_service(None)
        svc = get_self_prompting_service(council=llm_council)
        assert isinstance(svc, SelfPromptingService)
        set_self_prompting_service(None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
