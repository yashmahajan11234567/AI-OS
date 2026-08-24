# COUNCIL SYNTHESIS ARCHITECTURE (TESTING PERSPECTIVES)

**Terminal 1 — Read-Only Reconciliation**
**Date:** 2026-08-23
**Scope:** Design the decision flow for multi-perspective test findings (PART 15). Adopts Karpathy LLM Council + evisoft Council *techniques* into the existing `CouncilManager` — never a second council.

> Evidence: `CouncilManager` (`core/council_manager.py:115`) already has 5 consensus algos, `CouncilMember.expertise`, `CouncilVote`, `dissent()`. `FinalJudgeAgency` (`core/ai_agency.py:507`) aggregates findings. KKC/EVC are technique-only (WebFetch). `[AI-OS SOURCE]` `[EXTERNAL]`

---

## 1. THE EXISTING COUNCIL IS SUFFICIENT — EXTEND, DON'T REPLACE

AI-OS `CouncilManager` already provides the synthesis substrate:
- `convene()` → assembles members with `expertise`.
- `propose()` / `vote()` / `decide()` → deliberation + consensus (UNANIMOUS/MAJORITY/SUPERMAJORITY/WEIGHTED/RANKED_CHOICE).
- `dissent()` → explicit disagreement capture.
- `CouncilDecision.outcome` + `metadata`.

The **only gap** is a *critique stage* (staged blind cross-review + dissenter-override) and a *chairman/synthesis* role. Both are **additive** to `CouncilManager`, not a competing system.

---

## 2. DECISION FLOW (PART 15 required)

```
Tester A (Security)    → findings
Tester B (Performance) → findings
Tester C (Chaos)       → findings
... (9 agencies)
User Agent             → findings
        │
        ▼
Independent Evidence Normalization
  (TestOrchestratorService → TestingEvidence schema:
   perspective, target, severity, proof, provenance, confidence)
        │
        ▼
CouncilManager.convene(TestingCouncil)
  members = the perspectives (each an expert member)
        │
        ▼
STAGE 1 — propose()
  each perspective submits its verdict + findings
        │
        ▼
STAGE 2 — critique()        [NEW, adopts KKC + EVC techniques]
  ├─ anonymize member identities (KKC blind review)
  ├─ cross-rank on two axes: accuracy + insight (KKC)
  ├─ relabel-then-review: randomly relabel A–E, send to fresh
  │  reviewers to catch blind spots (EVC)
  └─ dissenter-override: chairman may side with a dissenting
     minority if its reasoning beats the majority (EVC)
        │
        ▼
STAGE 3 — synthesize() / decide()
  apply consensus algorithm (weighted by expertise/confidence)
        │
        ▼
FinalJudgeAgency → final verdict
  (APPROVE / REJECT / CONDITIONAL)  [existing]
        │
        ▼
AI-OS Verification (11-layer)
        │
   ┌────┴────┐
  PASS      FAIL
   │          │
COMPLETE   RCA → Learning → Replan → Re-execute → Retest
            (M3 closed loop remains the FINAL control loop)
```

---

## 3. TECHNIQUE ADOPTION (from KKC / EVC) — INTO CouncilManager

| Technique (source) | Where it lands in CouncilManager | How |
|---|---|---|
| Independent first-opinions (KKC, EVC) | `propose()` already isolates each perspective's submission | No change — perspectives submit independently |
| Anonymized cross-ranking, two axes (KKC) | NEW `critique()` stage | Strip `member_id` for the ranking pass; rank peers on `accuracy` + `insight` (two `CouncilVote` sub-scores) |
| Separate chairman model (KKC) | Dedicated `chair` `CouncilMember` with synthesis role | A distinct member (or MOA aggregator, M6) performs final merge |
| Worldview-diverse advisors (EVC) | `CouncilMember.expertise` assignment | Assign perspectives deliberately diverse stances |
| Relabel-then-review (EVC) | `critique()` randomization | Shuffle member labels before cross-review to break authority bias |
| Side-with-dissenter (EVC) | `decide()` override rule | If a dissenting `CouncilVote.reasoning` outranks majority on insight axis, adopt it |
| Disagreement detection | `dissent()` + `CouncilDecision.metadata` | Already present; surfaced in synthesis |

**No KKC/EVC code is vendored** (both unlicensed). Only the *techniques* are re-implemented inside the licensed AI-OS `CouncilManager`.

---

## 4. WHY NOT A SECOND COUNCIL (PART 5 rule enforced)

- **Karpathy LLM Council** = a local web app, no reusable boundary, unlicensed, "Saturday hack." Adopt technique, reject as subsystem.
- **evisoft Council** = SKILL.md prompt templates, 3 commits, no license. Adopt technique, reject as subsystem.
- **Ruflo** = kernel competitor. REFERENCE only.
- **Hermes MOA** = synthesis *technique* (M6), callable from `CouncilManager`, off by default.
- **One `CouncilManager`** remains the sole governance/synthesis authority. The TestingCouncil is one `CouncilSession` among the 9 governance councils — a *testing-domain* council, not a parallel hierarchy.

---

## 5. INDEPENDENCE IN SYNTHESIS (ties to PART 13)

- The **builder** of the target under test is **excluded** from the TestingCouncil membership.
- Each perspective votes once; `weighted` consensus prevents any single perspective dominating.
- The `chair`/`FinalJudge` is AI-OS-owned (never Hermes, never an external model acting autonomously).
- Disagreement is *preserved* (dissent captured), not silently averaged away.

---

## 6. ACCEPTANCE CRITERIA (future M7)

1. A TestingCouncil convenes with ≥9 perspective members + User Simulation; builder excluded.
2. `critique()` produces an anonymized two-axis cross-ranking and applies dissenter-override when a minority insight outranks.
3. `FinalJudgeAgency` emits a deterministic verdict consumable by AI-OS verification.
4. On FAIL, the verdict + evidence route into the existing RCA→Learning→Replan→Re-execute loop (no parallel decision loop).
5. No external council subsystem is instantiated; KKC/EVC techniques live only inside `CouncilManager`.

---

*End of council synthesis architecture. Extends verified `CouncilManager` with a critique stage; adopts techniques, rejects subsystems.*
