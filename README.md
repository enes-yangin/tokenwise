# Cost & quality skills for Claude Code

A small toolkit that makes agentic work **cheaper and higher-quality without cutting
correctness** — plus the benchmark suite that measures (and bounds) every claim.

Two live skills, one clear split:

| Skill | Question it answers | Where it lives |
|---|---|---|
| **`/tokenwise`** | *How do I execute leanly?* — lean working mode + execution disciplines (recall don't re-derive, read surgically, generate lean, avoid rework, acceptance-check-first, external memory, cache discipline). Bundles `py-debug` / `tdd` / `git-commit` / `plan-critique`. | Plugin — see `tokenwise/README.md` |
| **`/route`** | *Where should this run?* — dispatch by cost: classify → ask about gaps → send mechanical bulk to a Haiku worker (carrying the `/tokenwise` execution disciplines) → hand the result back. Keeps reasoning/ambiguous/security work on Opus. Deliberately has **no built-in review** — reviewing is external, on you. | Standalone skill (`skills/route/SKILL.md`) |

> A former `/heavy` skill was **retired**: its content was absorbed into these two
> (orchestrator/worker routing → `/route`; acceptance-check-first, external-memory, cache
> discipline → `/tokenwise`). It no longer exists.

The one finding everything rests on, measured not assumed: on a strong model you **can't**
cut token *count* with a prompt-level skill (the baseline is already lean). The real win
is on **cost** — running well-specified bulk work on a cheaper model saves **~80–84% at
equal, objectively-judged quality**, across languages and task types.

---

## Which command, when

| Your situation | Reach for |
|---|---|
| Any task — you want a lean, no-waste default | **`/tokenwise`** (on by default via the plugin hook) |
| Long / multi-session task; avoid re-deriving context after compaction | **`/tokenwise`** — its external-memory (`NOTES.md`) discipline |
| Ambiguous or error-prone change; want to avoid building the wrong thing | **`/tokenwise`** — its acceptance-check-first discipline |
| A task with a big **mechanical bulk** (bulk codegen, edits, scans, first-draft) and you want ~5× cheaper | **`/route`** — it delegates that bulk to a disciplined Haiku worker; you do a light check yourself, no built-in Opus review |
| Underspecified request where a cheap model would guess wrong | **`/route`** — it asks you to fill the gaps *before* delegating |
| A Python error, failing test, or traceback | `py-debug` (auto-triggers) |
| Implementing new Python behavior / a bug fix that should stay fixed | `tdd` (auto-triggers) |
| Committing or splitting changes | `git-commit` (auto-triggers) |
| A risky, irreversible, or hard-to-reverse plan | `plan-critique` (auto-triggers) |

Rule of thumb: **`/tokenwise` is the *how*, `/route` is the *where*.** They compose — use
`/route` to dispatch a big task cheaply, with `/tokenwise` disciplines governing how each
part is executed. For a quick, well-specified one-file edit, you need neither — the
defaults already handle it.

---

## Setup

**`/tokenwise`** (plugin, bundles the four workflow skills): follow `tokenwise/README.md`
— `/plugin marketplace add <path>` then `/plugin install tokenwise@tokenwise`.

**`/route`** (standalone skill):
```bash
mkdir -p ~/.claude/skills/route
cp skills/route/SKILL.md ~/.claude/skills/route/SKILL.md   # Windows: C:\Users\<you>\.claude\skills\route\
```
No build step. Start a new session; it appears as `/route`. A skill is a single
`SKILL.md` (YAML frontmatter + Markdown body); the `description` is what Claude matches
to decide when to trigger it.

**To reproduce the benchmarks** you need a Python venv with FastAPI + pytest, and `node`
for the JS grader:
```bash
python -m venv .venv
./.venv/Scripts/python.exe -m pip install fastapi httpx uvicorn pytest pytest-cov
```

---

## Usage example — `/route`

```
/route add an "orders" resource to this API
```
It will: (1) classify complexity, (2) ask you about any unstated decisions (status codes,
edge-case behavior, scope), (3) send the now-clear mechanical work to a Haiku worker
(~5× cheaper) or keep complex/ambiguous/security work on Opus, then hand the result back.
It does **not** run a built-in Opus review — that would cost ≈ a full Opus run and erase
the saving — so reviewing the output stays with you (a light test-run is usually enough
on clear work).

`/route` is a skill **you invoke**, not a transparent hook — Claude Code can't swap the
session model per-prompt or prompt you for gaps from inside a hook. A fully automatic
router would need an external pre-prompt classifier.

---

## Benchmark results

Every implementation task is graded by an **independent hidden judge** the agents never
saw. Prices (June 2026, blended 90/10): **Opus 4.8 ≈ $7.0/M**, **Sonnet 4.6 ≈ $4.2/M**,
**Haiku 4.5 ≈ $1.4/M** — a **5×** gap between Opus and Haiku.

### Finding 1 — a prompt-skill can't cut token *count*

Same task, same model, an efficiency ruleset ON vs OFF:

| Task | Model | ON | OFF | Judge | Outcome |
|---|---|--:|--:|:--:|---|
| Deep REST API | Opus | 42,395 | 40,815 | 7/7 = 7/7 | tie (ON +4%) |
| "orders" feature | Sonnet | 51,950 | 48,859 | 12/12 = 12/12 | tie (ON +6%) |

The baseline already greps, reads surgically, batches, and avoids re-reading — telling it
to do so again buys ~0 tokens and can add small overhead. (This is *why* the token-count
goal was abandoned and why `/heavy` was retired.)

### Finding 2 — model routing cuts *cost* ~80–84% at equal quality

Same task, run on each model; cost = tokens × price. `/route`'s core lever.

| Task | Opus | Haiku | Saving | Quality |
|---|--:|--:|:--:|:--:|
| Investigate 908-file Django repo | $0.233 | $0.038 | **83.8%** | equal |
| Implement "orders" feature (judged) | $0.337 | $0.067 | **80.1%** | 12/12 = 12/12 |
| Same task, repeated **n=3** | $0.241 avg | $0.038 avg | **84.4%** | equal (Haiku slightly noisier) |

The token counts are near-equal — the saving is almost entirely **price**, robust to the
unknown input/output split (both models share the 5:1 ratio).

### Finding 3 (NEWEST) — the routing saving generalizes across domains

`/route`'s cheap-model routing was previously measured mostly on Python/FastAPI CRUD.
This run tests four unrelated domains, each with an independent hidden grader:

| Domain | Task | Haiku | Opus | Saving |
|---|---|:--:|:--:|:--:|
| Python (algorithmic) | TTL-aware LRU cache | **10/10** · $0.032 | **10/10** · $0.198 | 84% |
| JavaScript | query-string parse/stringify | **15/15** · $0.031 | **15/15** · $0.195 | 84% |
| SQL | analytics queries | **4/4** · $0.033 | **4/4** · $0.203 | 84% |
| Contextual | cross-file code comprehension | **6/6** · $0.040 | **6/6** · ~$0.26\* | — |

On clear/mechanical work Haiku matched Opus **perfectly in every domain**, at ~5× lower
cost. The routing decision is not Python-specific. (\* Opus contextual cost is inflated by
a re-verification rerun and excluded from the aggregate; its quality parity still holds.)
Write-up: `benchmark_route/BENCHMARK_ROUTE.md`.

### Finding 4 — but ambiguity breaks the cheap path (the load-bearing caveat)

Same "orders" feature, same judge, edge cases **stated** vs **left unstated**:

| Spec | Opus | Haiku |
|---|:--:|:--:|
| Clear (edge cases listed) | 12/12 | **12/12** |
| Vague (edge cases unstated) | 10–11/12 | **8/12** |

On a vague spec Haiku missed unstated rules Opus inferred. **This is why `/route`
disambiguates before delegating: it's economically necessary, not polish.**
Write-up: `benchmark_heavy/BENCHMARK_RIGOR.md`.

### Finding 5 (NEWEST) — a built-in review erases the saving, so `/route` doesn't do one

The full pipeline was measured end-to-end on the vague spec: Opus disambiguates → a
disciplined Haiku worker implements → Opus reviews against the now-clear spec.

| Stage | Cost |
|---|--:|
| Opus disambiguate | $0.298 |
| Haiku worker (disciplined) | **$0.062** |
| Opus review | $0.346 |
| **Full pipeline** | **$0.706** |
| *vs.* all-Opus, same task | $0.324 |
| *vs.* plain Haiku, no pipeline | $0.063 |

The pipeline cost **2.2× all-Opus** — the Haiku worker is only $0.06 of the $0.71; the
two Opus stages are 91% of the bill. The review stage alone (**$0.346**) costs about as
much as just letting Opus do the whole task, because a full re-audit has to read the
same spec and code an implementation pass would. And in this run the review found
**nothing to fix** — the worker had already implemented the (disambiguated) spec
faithfully; the judge gap was the *disambiguator's* interpretation diverging from the
hidden grader, not a worker defect a review could catch.

**Consequence:** `/route` does not run a built-in review. A heavy Opus re-audit is worth
paying for only on genuinely risky output (security, irreversible, correctness-critical)
— and that's a deliberate choice you make externally, in view of the cost, not an
automatic step the router takes. On clear/mechanical work a light test-run check is
enough (Haiku already matches Opus 12/12 there); on a single bounded vague task, the
full pipeline doesn't beat just using Opus. Write-up: `benchmark_heavy/BENCHMARK_PIPELINE.md`.

### Bottom line

| Question | Answer |
|---|---|
| Can a prompt-skill cut token **count**? | No — the baseline is already lean (Finding 1). |
| Can routing cut **cost**? | Yes — **~84%** at equal quality on clear work, across languages/domains (Findings 2–3). |
| Does it always work? | No — ambiguous/reasoning work must stay on Opus; disambiguation is what makes the cheap path pay (Finding 4). |
| Is a stronger model worth it on simple/localized work? | No — Haiku matches Opus at 1/5 cost. |
| Should the router review its own worker's output? | No — a built-in Opus review costs ≈ all-Opus and erases the saving; review is external and deliberate (Finding 5). |

Everything is **n=1 per cell** unless marked `n=3`; the graders are objective, but treat
each number as a data point, not a proof. The consistency of the ~84% figure across
independent domains is the real signal.

---

## Repository layout

```
skills/route/SKILL.md         # the /route skill (version-controlled source)
tokenwise/                    # the /tokenwise plugin (its own README + benchmark)
benchmark_deep/               # skill-ON-vs-OFF runs (deep REST API; holds the shared .venv)
benchmark_heavy/              # cost, vague-spec, rigor pass; judge_orders.py (hidden judge)
  BENCHMARK_RIGOR.md          #   repetition / Sonnet / debugging write-up
  BENCHMARK_PIPELINE.md       #   NEWEST: full disambiguate→worker→review measured end-to-end
benchmark_route/              # NEWEST: cross-domain routing benchmark
  judge_lru.py, judge_qs.js, judge_sql.py   # hidden graders (agents never saw them)
  BENCHMARK_ROUTE.md          #   cross-domain write-up
```

## Honest limitations

- Savings are **cost**, not token count; on a strong model token count is already lean.
- The cheap path is only safe on **clear** work — hence `/route`'s disambiguation step.
- `/route` is invoked, not a transparent auto-router.
- Benchmark token counts are single totals (no input/output split); the cost *ratio* is
  robust to this, the absolute dollars are approximate.
