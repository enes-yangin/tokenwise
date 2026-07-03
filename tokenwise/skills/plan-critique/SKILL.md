---
name: plan-critique
description: >-
  Plan, pre-mortem, then red-team your own plan through different personas before
  executing. Use this BEFORE starting any non-trivial, risky, or hard-to-reverse work —
  e.g. "plan this feature", "think this through", "what could go wrong", "stress-test
  this approach", "critique this plan", a refactor that touches many files, a migration,
  or anything you'd hate to undo. It front-loads thinking — lay out the full plan, find
  the problems and solve them up front, then attack the plan from several viewpoints —
  so you catch the expensive mistake on paper instead of after writing the code. This is
  the cheapest rework there is.
---

# Plan, pre-mortem, critique

The most expensive bug is the one baked into the plan — you build the wrong thing
correctly, then pay to discover it, undo it, and rebuild. This skill spends cheap
thinking tokens up front to avoid expensive rework tokens later (tokenwise lever 4).

Four phases, in order. Scale them to the task — a small change gets a light pass, a
risky migration gets the full treatment.

## Phase 1 — Plan it fully

Lay out the actual approach before any critique:

- **Goal**: what done looks like, in one or two sentences. The real outcome, not the
  task restated.
- **Steps**: the concrete sequence. Specific enough to act on.
- **Touch points**: files, components, data, external systems this affects.
- **Assumptions**: what you're taking for granted. Name them — they're where critique
  bites hardest.

If the goal itself is ambiguous, resolve that with the user *now*; a perfect plan for
the wrong goal is worthless.

## Phase 2 — Pre-mortem (find the problems, then solve them)

Imagine it's shipped and it went wrong. Work backwards: what failed? Don't wait to hit
the problems during execution — surface them here, while they're cheap.

Scan these failure categories and list every plausible risk:

- **Correctness & edge cases** — empty/None/boundary inputs, the unhappy path.
- **Integration** — what else calls this? what assumptions do callers make?
- **Data & state** — migrations, backfills, concurrent access, partial failure.
- **Security & trust** — untrusted input, secrets, permissions, injection.
- **Reversibility** — can this be undone? what's the blast radius if it's wrong?
- **Dependencies & environment** — new deps, version skew, "works locally" gaps.
- **Performance** — N+1, large inputs, hot paths.
- **Ambiguity** — requirements you're guessing at.

For each risk, write the **mitigation or solution** — not just the worry. A risk with no
plan is unfinished thinking. Resolve what you can decide now; explicitly flag what needs
the user. If a risk is severe and unmitigated, that may change the whole approach — loop
back to Phase 1.

## Phase 3 — Critique through personas

Now attack the plan from distinct viewpoints. Each persona is a different lens that
catches a different class of flaw; a single perspective has blind spots that another's
obsession covers. Give each one concrete findings tied to *this* plan, not generic
advice — and let them disagree. Real tension between personas is signal, surface it.

**Default panel** (pick the 2–3 most relevant for a small task; use the full set for
big or risky work, and add domain-specific personas as needed):

- **The Skeptic** — "What's the hidden assumption that makes this collapse? What happens
  at the seams you're hand-waving?" Hunts the load-bearing guess.
- **The Simplifier** (ponytail spirit) — "This is over-built. Does this part need to
  exist at all? What's the version with half the moving parts?" Hunts unnecessary code,
  abstractions, and dependencies.
- **The Security/Safety officer** — "Where does untrusted data enter? What's
  irreversible? What breaks under malice or bad input?" Hunts trust-boundary and
  blast-radius problems.
- **The Maintainer (you, in six months)** — "Will the next person understand this? Is it
  testable? What's the implicit knowledge that isn't written down?" Hunts future pain.
- **The User / Product owner** — "Does this actually solve the real problem, or a
  proxy for it? Are we building the right thing well?" Hunts misaligned goals.

Add when relevant: **Performance/Ops** (scale, observability, rollback),
**Accessibility**, **Data integrity**, **Cost**.

For each persona, output its sharpest 1–3 findings. A persona with nothing to add says
so in a line — don't manufacture objections.

## Phase 4 — Synthesize

Fold the critique back into a final plan:

- **What changed** and why (which finding drove it).
- **Risks consciously accepted** — name them and the reason they're acceptable. Not
  every risk must be eliminated; some are fine if you've *chosen* them with eyes open.
- **Open questions for the user** — the decisions that are genuinely theirs.

Then present the revised plan (or proceed, if the work is yours to run). The output is a
plan you've already argued with and won, not a first draft.

## Intensity

- **lite**: a quick plan, a short pre-mortem of the top 2–3 risks, and 2 persona lenses
  (usually Skeptic + Simplifier). For moderate tasks where you want a sanity pass
  without a full ceremony.
- **full**: the complete four phases with the full persona panel. For large, risky, or
  irreversible work where a wrong plan is genuinely costly.

Match the ceremony to the stakes. Running the full panel on a one-line fix wastes the
very tokens this skill exists to save — that itself is a tokenwise failure.

## The one rule

Don't start executing a non-trivial plan you haven't argued against. If you can't name
one risk and one persona's objection, you haven't thought about it yet — and an
unexamined plan is where the expensive rework comes from.
