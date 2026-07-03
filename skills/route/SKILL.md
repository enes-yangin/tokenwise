---
name: route
description: >-
  Cost-routing front door for a task: classify the request, ASK the user about any
  semantic gaps FIRST (ambiguity is exactly what makes a cheap model fail), then send
  simple/well-specified/mechanical work to a Haiku worker (~5x cheaper, ~80% lower
  cost) and keep complex/ambiguous/reasoning/security work on Opus. Grounded in
  benchmarks: on a CLEAR spec, Haiku matched Opus quality (12/12 objective judge) at
  ~80% lower cost; on a VAGUE spec, Haiku missed unstated edge cases (8/12 vs Opus
  10-11/12). So the router's job is to remove ambiguity before delegating. Use it when
  the user wants prompts auto-dispatched by cost/complexity, or asks to route simple
  work to Haiku and hard work to Opus. Companion to /heavy and /tokenwise.
---

# Route — disambiguate, then dispatch by cost

A cheap model is not a worse model on well-specified work — it's a worse *guesser*.
Benchmark: given a clear spec, Haiku produced an implementation that passed the same
objective 12/12 edge-case judge as Opus, at ~80% lower cost. Given a vague spec (edge
cases unstated), Haiku missed them (cancel-idempotency, wrong status codes) while Opus
inferred most. **The lever that unlocks cheap routing is removing ambiguity** — so this
skill asks the user to fill gaps before it sends anything to the cheap worker.

Run these steps in order. Do not skip step 2.

## Step 1 — Classify on two axes

Judge the task on **ambiguity** (how underspecified) and **complexity** (how much
genuine reasoning/judgment correctness requires).

**Mechanical / low-complexity** (Haiku candidates): bulk edits, renames, format
conversions, file/codebase scans and extraction, boilerplate or codegen from a clear
spec, wiring up a known pattern, running tests and reporting, mechanical refactors.

**High-complexity** (Opus only): architecture and design decisions, subtle correctness
or concurrency/edge-case reasoning, security-sensitive changes, debugging an unknown
root cause, anything where "what is correct" is itself a judgment call.

## Step 2 — Resolve semantic gaps with the user (do NOT skip)

This is the step that makes cheap routing safe. List the decisions the prompt leaves
open — the unstated rules a wrong guess would get wrong — and ask the user with
AskUserQuestion before routing. Typical gaps:

- Unspecified edge-case behavior (what happens on conflict, empty input, over-limit,
  double-action, missing reference).
- Unstated contract details (status codes, response shape, naming, return on not-found).
- Ambiguous scope ("add orders" — with cancellation? reporting? validation?).
- Quality/perf/security expectations not stated.

Ask only the gaps that materially change the implementation; don't interrogate. After
the answers, the task should be specified well enough that correctness is well-defined.
**If you cannot make it unambiguous, treat it as high-complexity and route to Opus.**

## Step 3 — Dispatch

- **Clear + mechanical → Haiku worker.** Spawn a subagent with `model: "haiku"`, handing
  it the now-disambiguated spec. This is where the ~80% cost saving lives.
- **Complex / residual-ambiguity / security → Opus.** Handle on Opus (the session model
  if it's Opus, or an `model: "opus"` subagent).
- **Mixed task → Opus orchestrates, Haiku executes the parts.** Opus does the design and
  the gap-resolution; delegate the mechanical sub-tasks (scans, bulk codegen, edits)
  to Haiku workers. This is the orchestrator/worker pattern (see /heavy delta 3).

**Second dial — effort, not just model.** Opus 4.8 bills thinking tokens like output, so
reasoning depth is a cost lever too. Match effort to the task: a simple lookup or short
mechanical step wants **low** effort (the model answers directly, spending almost no
thinking tokens); genuine multi-step reasoning, debugging, or design wants **high/max**.
Don't pay max-effort thinking on work that doesn't need it — that's wasted output-priced
tokens even on the cheap model. So the full routing decision is two dials: *which model*
(Haiku vs Opus, ~5x price gap) and *how much effort* (low→max, thinking-token cost).

## Step 4 — Review before accepting (especially Haiku output)

The cheap worker's output gets a correctness pass from the orchestrator: run the
tests/acceptance check, and specifically re-check the edge cases the spec involved
(the things Haiku is most likely to miss when judgment is needed). If the worker missed
something, either fix it on Opus or hand it back with the specific gap named. The review
is small (Opus tokens) relative to the worker's bulk, so cost stays far below all-Opus.

## The "never cut" band

Route UP, never down, when unsure. Security-sensitive work, ambiguous correctness, and
anything where a wrong guess is expensive or hard to reverse goes to Opus regardless of
how "simple" it looks. The cost saving is never worth a wrong result on work that
mattered. When the task is genuinely clear and mechanical, route down with confidence —
that's where the ~80% lives.
