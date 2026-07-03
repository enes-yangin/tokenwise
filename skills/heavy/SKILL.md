---
name: heavy
description: >-
  The few token/quality disciplines for heavy tasks that Claude does NOT already do
  on its own. Modern Claude Code already greps before reading, reads surgically,
  batches parallel tool calls, avoids re-reading, and delegates exploration to
  subagents — re-instructing those buys nothing (benchmarked: ~0 token change on a
  908-file repo, because the baseline already does them). This skill is only the
  delta: (1) write a runnable acceptance check BEFORE implementing, especially when
  the spec is ambiguous or the change is error-prone — this is what kills rework, the
  biggest hidden cost; (2) keep an external scratchpad (NOTES.md) on long multi-step
  tasks so decisions survive compaction instead of being re-derived; (3) split work
  orchestrator/worker so the bulk runs on a cheap model (Haiku, ~5-10x cheaper) while
  the strong model only plans and reviews; (4) don't invalidate the prompt cache
  (cached input ~90% cheaper) by churning or reordering context. The real >=50% gain is
  on COST (levers 3-4), not raw token count — the baseline is already lean. Use it when
  starting a wide, long, or ambiguous task where rework, context loss, and model-cost
  are the real risks — not for quick edits. Companion to /tokenwise.
---

# Heavy — only what Claude doesn't already do

Most "token-saving" advice for agents is already baseline Claude Code behavior. We
benchmarked the obvious levers (grep-first, surgical reads, subagent fan-out,
programmatic extraction) on a 908-file repo: the agent told to "extract
programmatically" used ~the same tokens as the plain agent, because **the plain agent
already greps by default**. Re-instructing default behavior is pure overhead — it's
why a verbose "do TDD, read surgically, fan out" skill measured slower and slightly
more expensive than no skill at all.

So this skill is deliberately the *delta*: the handful of disciplines that genuinely
change behavior because Claude does NOT do them on its own. Apply these; don't waste
tokens re-stating the defaults below.

**Where the real ≥50% lives: cost, not token count.** Re-stating defaults can't cut the
token *count* — the baseline is already lean. The large wins are on *cost*: running the
bulk of the work on a cheap model (delta 3, ~5–10x) and not invalidating the prompt
cache (delta 4, cached input ~90% cheaper). Those two are the levers that actually move
the bill; the other two (acceptance check, external memory) protect quality and prevent
rework on long/ambiguous work.

## What Claude already does — do NOT re-instruct

Assume these are on. Telling yourself to do them again is wasted context:

- Greps/globs to locate before reading; reads with offset/limit, not whole files.
- Batches independent tool calls in one turn.
- Tracks file state — doesn't re-read a file it already read or just edited.
- Acts on what's already established instead of re-deriving it.
- Delegates broad exploration to Explore subagents when the repo is large.
- Prefers a recommendation over an options survey; keeps output lean (also /tokenwise).
- Filters obviously, e.g. piping a noisy log/test run down to the failing lines.

If a behavior is on this list, it does not belong in a skill, a prompt, or your plan.

## The delta — what actually changes behavior

### 1. Acceptance check BEFORE implementation

Claude will happily start editing before pinning down what "done" means — and on an
ambiguous or error-prone task that leads to the most expensive thing there is: rework
(wrong change → discover → undo → redo, every step re-paying context).

- Before touching implementation, write the runnable check that proves the task done —
  the test, the assertion, the command whose output you'll grade. Include the edge
  cases you can already name.
- Run it; confirm it fails for the right reason (a real baseline, not a typo).
- Implement the minimum to pass; run it every iteration.
- On failure, don't guess: read the actual error, form one hypothesis, confirm it, fix
  the cause once. (Use `/py-debug` for the full protocol on Python.)

Skip this only when the task is small and unambiguous — there the model gets it right
first try anyway and the check is just ceremony. Its payoff is ambiguity and risk.

### 2. External memory on long, multi-step tasks

Claude does not keep notes outside its context on its own, so when the window compacts,
hard-won structure gets re-derived (re-explored, re-read) at full cost.

- Keep a short `NOTES.md` (or use the scratchpad dir): the decisions made, the file map
  you built, what's done, what's open. Architectural decisions and unresolved issues —
  not raw tool output.
- Pull it back in instead of re-exploring. This is the lever that compounds across a
  long task: the exploration is paid once, not once per context window.
- Stable, recurring conventions go in CLAUDE.md, where they load once for free.

### 3. Orchestrator / worker split — the biggest cost lever

This is where real ≥50% *cost* savings live (the gain is cost, not raw token count).
Claude runs everything on one model by default; it won't downgrade itself for the easy
parts. You split the work by complexity:

- **Strong model orchestrates** — understands the goal, breaks it into subtasks,
  evaluates outputs, decides next steps. This is a small fraction of the tokens.
- **Cheap model executes** — spawn workers with `model: "haiku"` for the bulk: wide
  searches, file reads, mechanical edits/renames, bulk codegen, first-draft tests.
- The published pattern runs ~2–3k orchestrator (Opus) tokens against ~15–25k worker
  (Haiku) tokens. Since the cheap model is roughly a tenth the price, total cost drops
  ~5–10x with no meaningful quality loss — the strong model still reviews the result.
- Even a two-call version (plan on the strong model, execute on the cheap one) pays.
  Reserve the expensive model for reasoning and the final review; delegate the rest.
- **Second dial: effort.** Opus 4.8 bills thinking tokens like output, so match effort to
  the step — low effort for simple/mechanical steps (near-zero thinking), high/max only
  for the reasoning that needs it. Don't pay deep thinking on shallow work. (See /route.)

### 4. Don't break the cache you're already getting

Prompt caching makes a cached prefix ~90% cheaper, and it's automatic — but YOU
invalidate it. Real deployments swung cache hit rates from 7%→74% just by stopping the
churn. The discipline is to not break a cache you'd otherwise get:

- **Keep the context stable and append-only.** Don't reorder, re-dump, or re-read
  files already in context; every change past a point invalidates the cache for
  everything after it.
- **Keep per-turn-varying content out of stable regions.** Don't inject timestamps,
  fresh IDs, or scratch data into the top of a long-lived context — put volatile stuff
  at the end.
- **Batch within the 5-minute window.** Cache entries live ~5 min; related sub-steps
  done close together hit the warm cache instead of paying full read price again.

## When to use it

Reach for `/heavy` when the task is **wide, long, or ambiguous** — a cross-cutting
change across many files, a multi-session effort, or a spec you'll have to nail down as
you go. That's where rework and context loss (the things the delta targets) actually
cost you. For a quick, well-specified edit, skip it: the defaults already handle that,
and the discipline is just overhead.

## The "never cut" band

These are never traded for tokens: understanding the problem, the acceptance check
itself, input validation at trust boundaries, error handling, security, accessibility,
and anything the user explicitly asked for. If a "lean" version would be wrong or less
than asked, it isn't lean — spend the tokens.
