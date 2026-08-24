"""
M7-J — SimplificationGate unit tests.

Covers:
  * over-engineering anti-patterns are detected (Adapter-of-Adapter, "A of B")
  * duplication detection
  * unnecessary-abstraction detection
  * REQUIRED safeguards are preserved (never fail purely for a security/isolation
    marker that legitimately adds complexity)
  * gate PASS/FAIL verdicts are bounded and deterministic
"""

from __future__ import annotations

import pytest

from aios.core.simplification_gate import (
    GateResult,
    GateVerdict,
    SimplificationGate,
)
from aios.core.testing_evidence import (
    Provenance,
    TestingEvidence,
)


def _prov():
    return Provenance(
        source="architecture_agency",
        worker="local",
        session="arch_abc12345",
        timestamp="2026-08-24T00:00:00+00:00",
        environment="tester",
        correlation_id="cid",
        test_id="t",
    )


def _ev(verdict="pass", severity="low"):
    return TestingEvidence(
        perspective="architecture_agency", target="x", test_id="t",
        severity=severity, confidence=0.9, reproducibility=1.0,
        verdict=verdict, provenance=_prov(),
    )


# ---------------------------------------------------------------------------
# Over-engineering
# ---------------------------------------------------------------------------

def test_adapter_of_adapter_detected():
    gate = SimplificationGate()
    impl = "class SecurityAuthAdapterOfAdapter:\n    pass\n"
    res = gate.evaluate(impl, [_ev()])
    assert res.verdict == GateVerdict.FAIL
    assert any("Over-engineering" in f for f in res.findings)


def test_a_of_b_naming_detected():
    gate = SimplificationGate()
    impl = "class Manager_of_Service:\n    pass\n"
    res = gate.evaluate(impl, [_ev()])
    assert res.verdict == GateVerdict.FAIL


def test_simple_implementation_passes():
    gate = SimplificationGate()
    impl = "def login(u, p):\n    return db.auth(u, p)\n"
    res = gate.evaluate(impl, [_ev()])
    assert res.verdict == GateVerdict.PASS
    assert res.safeguard_preserved is True


# ---------------------------------------------------------------------------
# Duplication
# ---------------------------------------------------------------------------

def test_duplication_detected():
    gate = SimplificationGate()
    line = "    result = compute_expensive_thing(payload)"  # len >= 12
    impl = "\n".join([line] * 3)
    res = gate.evaluate(impl, [_ev()])
    assert res.verdict == GateVerdict.FAIL
    assert any("duplication" in f.lower() for f in res.findings)


# ---------------------------------------------------------------------------
# Unnecessary abstraction
# ---------------------------------------------------------------------------

def test_pass_through_wrapper_detected():
    gate = SimplificationGate()
    impl = (
        "class Proxy:\n"
        "    def foo(self):\n"
        "        return self._inner.foo()\n"
        "    def bar(self):\n"
        "        return self._inner.bar()\n"
    )
    res = gate.evaluate(impl, [_ev()])
    assert res.verdict == GateVerdict.FAIL


# ---------------------------------------------------------------------------
# Safeguard preservation (INV: gate must not strip required safeguards)
# ---------------------------------------------------------------------------

def test_security_safeguard_preserved():
    gate = SimplificationGate()
    # auth/authorize present -> required safeguard; should NOT fail purely for it.
    impl = "def login(u, p):\n    if not authorize(u, 'login', svc): return None\n    return db.query(u, p)\n"
    res = gate.evaluate(impl, [_ev()])
    assert res.safeguard_preserved is True
    assert res.verdict == GateVerdict.PASS


def test_isolation_safeguard_preserved():
    gate = SimplificationGate()
    impl = (
        "def dispatch(uid):\n"
        "    session_id = make_isolated_session(uid)\n"
        "    provenance = attach_provenance(session_id)\n"
        "    emit_event('DISPATCH', provenance)\n"
    )
    res = gate.evaluate(impl, [_ev()])
    assert res.safeguard_preserved is True
    assert res.verdict == GateVerdict.PASS


def test_gate_result_has_passed_property():
    gate = SimplificationGate()
    res_pass = gate.evaluate("def f(): return 1\n", [_ev()])
    assert isinstance(res_pass, GateResult)
    assert res_pass.passed is True
    res_fail = gate.evaluate("class AdapterOfAdapter:\n    pass\n", [_ev()])
    assert res_fail.passed is False


def test_score_bounded_between_zero_and_one():
    gate = SimplificationGate()
    res = gate.evaluate("class AAofA:\n    pass\n", [_ev()])
    assert 0.0 <= res.score <= 1.0
