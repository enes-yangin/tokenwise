# Report — What's Actually Valuable Here

This session produced two skills, ~14 benchmark runs, a live-verified sample app, and a
lot of numbers. Most of the numbers are not the point. This report separates the parts
worth remembering from the parts that were noise, dead ends, or one-off scaffolding.

---

## The one finding worth keeping

**Cost, not token count, is the lever — and it only pays off on clear/well-specified
work.**

- Re-instructing Claude to be "efficient" (grep-first, TDD, surgical reads) buys ~0
  token savings on a strong model, because the baseline already does it. Confirmed
  4 separate times (Parts 1 and the v2 replication). This killed the original plan
  ("50% token reduction via a prompt skill") — correctly, before it wasted more effort.
- Running the bulk of a task on Haiku instead of Opus cuts **cost by ~80–84%**, at
  **equal objectively-judged quality**, provided the spec is clear. This reproduced
  across unrelated task types: a codebase investigation, a backend feature build, and
  a React frontend build. Three different tasks, same ~80% number. That consistency is
  the actual evidence, not any single run.
- **The one counter-intuitive result that matters most:** on a vague spec, the
  "cheap worker + strong reviewer" pipeline was *not* cheap — it cost 41% *more* than
  running everything on Opus, because repairing broken output costs as much as writing
  it fresh. This is the finding that justifies `/route`'s design (ask about gaps before
  delegating) as an economic necessity, not a nicety. Without this result, "disambiguate
  first" would just be a plausible-sounding rule; with it, it's a rule with a measured
  cost of skipping it.

Everything else in this session is in service of, or a caveat on, this one finding.

---

## Two real, durable artifacts

- **`/heavy`** (`skills/heavy/SKILL.md`) — discipline for wide/long/ambiguous tasks.
  Worth keeping because it's short and encodes only what Claude doesn't already do
  (acceptance-check-first, external memory, orchestrator/worker split, cache
  discipline). It went through real revision: an earlier version re-stated baseline
  behavior and measured *worse* than no skill at all (Part 1, run #3) — that failure is
  why the current version is this lean. The skill is smaller because a benchmark said
  "cut this."
- **`/route`** (`skills/route/SKILL.md`) — the classify → ask-gaps → dispatch → review
  loop. This is the one piece of the whole session that turned a finding into a
  reusable procedure. It was also the one thing actually *used* on a real task (the
  crypto portfolio build), not just benchmarked in the abstract.

---

## What's honestly weak or should not be over-trusted

Being direct about this matters more than padding the report with wins.

- **Every single-run (n=1) quality comparison is noisy and shouldn't be quoted as a
  fact.** The v1→v2 replication of the exact same skill-vs-no-skill benchmark flipped
  which model/condition "won" on the same bug category (DB isolation) between runs.
  The only n≥3 result (Django investigation) showed cost saving is tight (±5%) but
  quality variance is real (Haiku missed a sub-answer in 1 of 3 runs; Opus gave up on
  one sub-question in 1 of 3 runs). Anywhere this report or the README says "Haiku
  matched Opus 12/12" — true for that run, not a guarantee.
- **The exact dollar figures are already perishable.** They're pinned to June 2026
  pricing. The *ratio* (Haiku ≈ 1/5 of Opus) is the durable part; the absolute cents
  are not.
- **The debugging benchmark was a null result, not a finding.** A well-localized bug
  (one failing test pointing straight at one function) was fixed by Haiku, Sonnet, and
  Opus alike. This does NOT show cheap models are fine at debugging in general — it
  shows they're fine at *easy* debugging. The claim "reasoning models pull ahead on
  hard bugs" remains untested. Don't cite this as "debugging is cheap now."
- **The Sonnet data point is thin.** One clear-spec build, one localized-bug fix — both
  showed Sonnet added cost with no quality gain over Haiku. That's real, but it's one
  task type; Sonnet's actual niche (something between Haiku's ceiling and Opus's
  necessity) was never found because nothing in this session's tasks needed it.
- **The crypto portfolio app is a demo, not a benchmark.** It's useful as a live,
  visual proof that `/route`'s output actually runs in a browser — the CoinGecko
  rate-limit incident during testing was a genuinely useful accidental check (it proved
  the frontend's graceful-degradation fallback works under real failure, not just in
  code review). But it doesn't add a data point to the cost-saving claim beyond what
  the "orders API" build already showed at higher rigor (independent judge vs.
  eyeballing a screenshot).
- **The original "skill vs no-skill TDD" hypothesis was never supported.** Across both
  replications, on Opus the skill added cost with no quality gain; on Haiku the winner
  flipped between runs. If a future session picks this thread back up, don't start
  from "skills probably help on hard tasks" — start from "this was tested twice and
  didn't hold."

---

## What was pure overhead / shouldn't be repeated

- Re-running the exact same "skill vs no-skill" benchmark design from scratch without
  first checking whether it already existed (it did — from 2 days earlier in the same
  project). Caught late, cost real tokens. Lesson for next time: check `ls`/timestamps
  on a benchmark directory *before* designing a new one that looks suspiciously similar
  to something already in the repo.
- Trying to force browser interaction through a restricted computer-use tier before
  falling back to the CLI (`chrome --headless --screenshot`) approach that actually
  worked cleanly and faster. The headless route should be the *first* try for any
  future "verify this frontend visually" task when the Chrome extension isn't
  connected — not the fallback after several blocked attempts.

---

## Bottom line

If someone reads only one section of this project going forward, it should be: **route
by cost after removing ambiguity, not before** — and treat every specific number in the
benchmark files as illustrative of a direction (cost ≈ 80% down, quality noisy at n=1),
not as a guarantee to be quoted verbatim.
