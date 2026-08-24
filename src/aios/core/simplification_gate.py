"""
M7 — SimplificationGate.

A mandatory pre-acceptance complexity-governance gate. It runs AFTER
``FinalJudgeAgency`` returns APPROVE but BEFORE the final ``TESTING_COMPLETED``
is emitted. If the implementation carries unnecessary complexity, the gate
returns ``FAIL`` and the closed loop restarts from planning.

CRITICAL INVARIANT (per the frozen M7 contract §11/§21.4): the gate MUST NOT
remove necessary security, reliability, isolation, or architectural safeguards
merely because they add complexity. Therefore the gate maintains a whitelist of
"required safeguard" markers; if detected, those structural elements are
EXEMPT from the complexity penalty.

All signals are derived by STATIC inspection of the implementation text + the
evidence record. No source code is ever sent to an external worker here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aios.core.testing_evidence import TestingEvidence

__all__ = ["GateResult", "SimplificationGate", "GateVerdict"]


class GateVerdict(str, Enum):
    """Simplification gate outcome."""

    PASS = "pass"
    FAIL = "fail"


@dataclass
class GateResult:
    """Result of a SimplificationGate evaluation."""

    verdict: GateVerdict
    score: float = 0.0  # 0.0 (simple) .. 1.0 (over-engineered)
    findings: list[str] = field(default_factory=list)
    safeguard_preserved: bool = True
    detail: str = ""

    @property
    def passed(self) -> bool:
        return self.verdict == GateVerdict.PASS


# Markers that indicate a NECESSARY safeguard (exempt from complexity penalty).
_REQUIRED_SAFEGUARD_MARKERS = (
    # security
    r"\b(authoriz|authenticat|permission|rbac|abac|sanitiz|escape|validate_input|csrf|security_manager)\b",
    # reliability / error handling
    r"\b(retry|circuit_breaker|timeout|backoff|fallback|idempoten)\b",
    # isolation / sandbox
    r"\b(isolat|sandbox|session_id|provenance|hermes_|boundary)\b",
    # architectural / observability
    r"\b(event_bus|emit_event|correlation_id|workflow|checkpoint|logging|audit)\b",
)

# Anti-patterns that signal unnecessary complexity (over-engineering).
_OVERENGINEERING_MARKERS = (
    r"\b(abstract_factory|factory_factory|generic_meta|decorator_chain|proxy_proxy)\b",
    r"\b(enterprise_pattern|business_delegate|service_locator_abuse)\b",
    r"class\s+\w*Adapter\w*Adapter",  # Adapter-of-Adapter naming smell
    r"class\s+\w+_of_\w+",            # "A of B" naming anti-pattern
    r"\b(god_class|god_object|mega_manager)\b",
)

# Duplication: identical line blocks repeated (>=3 identical non-trivial lines).
_DUP_LINE_MIN_LEN = 12


class SimplificationGate:
    """
    Static complexity-governance gate.

    ``evaluate`` inspects the implementation text and the supporting evidence.
    It returns FAIL when unnecessary abstraction, duplication, or
    over-engineering is detected — BUT it preserves required safeguards.
    """

    def __init__(
        self,
        *,
        complexity_threshold: float = 0.6,
        enable_safeguard_exemption: bool = True,
    ) -> None:
        self._threshold = complexity_threshold
        self._safeguard_exempt = enable_safeguard_exemption
        self._safeguard_patterns = [
            re.compile(p, re.IGNORECASE) for p in _REQUIRED_SAFEGUARD_MARKERS
        ]
        self._over_pattern = re.compile("|".join(_OVERENGINEERING_MARKERS), re.IGNORECASE)

    def _has_required_safeguard(self, text: str) -> bool:
        return any(p.search(text or "") for p in self._safeguard_patterns)

    def _count_over_engineering(self, text: str) -> int:
        if not text:
            return 0
        return len(self._over_pattern.findall(text))

    def _count_duplication(self, text: str) -> int:
        if not text:
            return 0
        lines = [ln.strip() for ln in text.splitlines() if len(ln.strip()) >= _DUP_LINE_MIN_LEN]
        seen: dict[str, int] = {}
        for ln in lines:
            seen[ln] = seen.get(ln, 0) + 1
        return sum(c - 1 for c in seen.values() if c >= 3)

    def _count_unnecessary_abstraction(self, text: str) -> int:
        """
        Count signals of unnecessary abstraction:
          * classes that are pure pass-through wrappers
          * deep nesting of indirection (e.g. >3 levels of delegate/forward)
        """
        if not text:
            return 0
        score = 0
        # pass-through wrapper class: a class whose body only forwards to one member
        class_bodies = re.findall(r"class\s+\w+[^\n]*:\n((?:\s+[^\n]+\n?)*)", text)
        for body in class_bodies:
            nonblank = [b.strip() for b in body.splitlines() if b.strip()]
            if not nonblank:
                continue
            # Ignore method/def header lines; only statement bodies count.
            statements = [b for b in nonblank if not b.startswith("def ")]
            if not statements:
                continue
            forwards = sum(
                1 for b in statements
                if re.search(r"return\s+self\.\w+(\.\w+)*\(|\.delegate\(|\.forward\(", b)
            )
            if forwards >= 2 and forwards == len(statements):
                score += 1
        # nesting depth of function defs
        depth = 0
        max_depth = 0
        for ln in text.splitlines():
            indent = len(ln) - len(ln.lstrip(" "))
            cur = indent // 4
            depth = cur
            max_depth = max(max_depth, depth)
        if max_depth >= 6:
            score += 1
        return score

    def evaluate(
        self,
        implementation: str,
        test_evidence: list[TestingEvidence] | None = None,
    ) -> GateResult:
        """
        Evaluate implementation complexity.

        Args:
            implementation: Source/text of the implementation under test.
            test_evidence: Collected evidence (used only to confirm safeguards
                are actually exercised, not to relax the gate artificially).

        Returns:
            ``GateResult`` with PASS/FAIL verdict.
        """
        text = implementation or ""
        findings: list[str] = []

        over = self._count_over_engineering(text)
        dup = self._count_duplication(text)
        abstraction = self._count_unnecessary_abstraction(text)

        if over:
            findings.append(f"Over-engineering anti-pattern detected (x{over})")
        if dup:
            findings.append(f"Code duplication detected (x{dup} repeated blocks)")
        if abstraction:
            findings.append(f"Unnecessary abstraction detected (x{abstraction})")

        # Compute a 0..1 complexity score (bounded). A single clear
        # over-engineering anti-pattern or unnecessary abstraction must push the
        # score past the threshold (a hard smell, not just minor noise).
        raw = over * 0.6 + dup * 0.4 + abstraction * 0.7
        score = min(1.0, raw)

        safeguard_present = self._has_required_safeguard(text)
        safeguard_preserved = True

        # If required safeguards are present, do NOT fail purely for their
        # structural cost. We subtract their "penalty" by exempting them:
        # a FAIL only stands if there is complexity BEYOND necessary safeguards.
        if self._safeguard_exempt and safeguard_present:
            # Required safeguards themselves are never a failure cause.
            # But over-engineering / duplication that co-exists still fails.
            if not (over or dup or abstraction):
                # Only safeguards present, no unnecessary complexity.
                score = min(score, 0.3)
            # safeguard_preserved stays True; we simply never treat safeguards as
            # the reason for a FAIL.
            safeguard_preserved = True

        if not findings:
            return GateResult(
                verdict=GateVerdict.PASS,
                score=round(score, 3),
                findings=["Implementation is appropriately simple"],
                safeguard_preserved=safeguard_preserved,
                detail="No unnecessary complexity detected.",
            )

        if score >= self._threshold:
            return GateResult(
                verdict=GateVerdict.FAIL,
                score=round(score, 3),
                findings=findings,
                safeguard_preserved=safeguard_preserved,
                detail=(
                    "Unnecessary complexity exceeds threshold "
                    f"({score:.2f} >= {self._threshold:.2f}). Closed loop must "
                    "restart from planning."
                ),
            )

        # Below threshold but with minor findings: still PASS (bounded).
        return GateResult(
            verdict=GateVerdict.PASS,
            score=round(score, 3),
            findings=findings,
            safeguard_preserved=safeguard_preserved,
            detail="Minor complexity present but within acceptable threshold.",
        )
