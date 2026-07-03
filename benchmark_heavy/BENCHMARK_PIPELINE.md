# /route full pipeline, measured end-to-end (vague spec)

The orchestrator+review pipeline was previously only interpolated. This measures every
stage on a **vague** spec, with a disciplined Haiku worker (the `/route` worker prompt
now carries the execution disciplines). Stages, each a separate agent for clean token
counts; final code graded by the independent 12-test judge.

## Stages & cost

| Stage | Model | Tokens | Cost |
|---|---|---:|---:|
| Disambiguate (vague → clear spec) | Opus | 42,601 | $0.298 |
| Implement from clear spec | **Haiku** (disciplined) | 44,317 | **$0.062** |
| Review against clear spec + fix | Opus | 49,451 | $0.346 |
| **Full pipeline** | | 136,369 | **$0.706** |

Baselines on the same vague spec: plain Haiku (no disambiguation, no review) **$0.063 →
10/12**; all-Opus (sibling project) **~$0.324 → 10–11/12**.

## What the judge said — and why it's not what it looks like

Final judge after review: **9/12** (review changed nothing — see below). But all **three**
failures are points where the Opus disambiguator resolved a genuinely-ambiguous rule
*differently than the hidden judge's author*, not worker or review defects:

| Judge test | Clear spec decided | Judge expects | Nature |
|---|---|---|---|
| create_order_basic | status `"active"` | `"pending"` | word choice |
| cancel_idempotency | 2nd cancel → **200** no-op (idempotent = safe repeat) | 409 | defensible interpretation |
| referenced_product_undeletable | product deletable, snapshot preserves history (204) | 409 | design policy |

The worker implemented the clear spec faithfully (16/16 of its own tests) and the Opus
reviewer, auditing against that same clear spec, **found nothing to fix**. So the worker
and review were spec-perfect; the 9/12 ceiling was set entirely by the orchestrator's
disambiguation choices diverging from a hidden human grader.

## The findings

1. **The full ceremonial pipeline is a false economy on a single bounded task.** At
   $0.706 it cost **2.2× all-Opus** ($0.324) and **11× the naive plain-Haiku** ($0.063).
   The cheap Haiku worker is only **$0.06 of the $0.71** — the two Opus stages
   (disambiguate + review) are 91% of the bill. Wrapping a Haiku worker in Opus on both
   ends means paying for Opus *twice* plus Haiku — more than just running Opus once.

2. **The review stage is the specific savings-killer.** An Opus review that must read the
   spec + all the code costs **≈ an Opus implementation** ($0.346 ≈ all-Opus $0.324).
   Even the realistic `/route` variant — where disambiguation is *AskUserQuestion* (the
   user answers, ~$0 model cost) instead of an Opus subagent writing a full spec —
   still lands at worker + review = **$0.408 > all-Opus**, because review alone ≈ all-Opus.
   Here the review also caught nothing (worker was spec-perfect), so its $0.35 was pure
   overhead.

3. **Disambiguation moves the risk, it doesn't erase it.** It converts "did the cheap
   model guess the unstated rule right?" into "did the *orchestrator's* interpretation
   match the grader's intent?" On genuinely-underspecified points, even a strong Opus
   orchestrator diverged from the hidden judge on 3 of 3 ambiguous rules — and no review
   fixes that, because review checks against the (already-diverged) clear spec, not the
   hidden judge.

## Consequence for `/route`

The ~80% savings (clear-domain benchmark) materialize only when you **don't** pay for a
full Opus review:

- **Clear / mechanical work** → route to Haiku, take a **light** correctness check
  (run the tests), not a full Opus re-audit. Haiku already matches Opus 12/12 here, so a
  heavy review is wasted money.
- **Genuinely vague / reasoning-heavy work** → the disambiguate+worker+review pipeline
  costs ≥ all-Opus and doesn't beat it. Just use Opus.
- The full pipeline only pays when the worker **bulk is large enough** (or many workers
  share one orchestration) that Haiku's share dominates the fixed Opus overhead — not on
  one bounded task where a single Opus review ≈ the whole job.
