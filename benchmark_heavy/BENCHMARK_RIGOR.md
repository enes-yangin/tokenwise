# Rigor Pass — the 3 gaps we closed

Targeted the three highest-value methodological gaps from the honest limitations list.
Prices (June 2026, blended 90/10): Opus $7.0/M, Sonnet $4.2/M, Haiku $1.4/M.

---

## Gap 1 — Run the orchestrator+review pipeline for real (+ review-catch rate)

We had only *estimated* the orchestrator variant. Now measured, on the **vague** spec
where Haiku alone scores 8/12: Haiku implements, then an Opus reviewer (given the 7
rules, not the judge) finds and fixes the misses.

| Approach | Cost | Judge | Note |
|---|---|---|---|
| All-Haiku (vague) | $0.071 | 8/12 | broken — misses atomicity, idempotency code, ref-integrity |
| All-Opus (vague) | $0.324 | 10–11/12 | infers most, still misses ref-integrity |
| **Pipeline: Haiku + Opus review** | **$0.458** | **12/12** | review caught **4/4** missed rules |

**Review-catch rate: 4/4 (100%)** — the review works. **But the cost finding is the
headline: the pipeline is the MOST expensive option (41% over all-Opus), not the
cheapest.** When the worker produces broken code, the review has to *repair* it (rewrite
the service, add tests) — costing as much as writing it fresh on Opus, on top of the
wasted Haiku run.

**Implication (the important one):** the orchestrator/worker cost saving is **real only
when the worker succeeds** — i.e. on a clear spec. On vague work the cheap path is a
false economy. This is the empirical proof that `/route`'s **disambiguation step is not
optional but economically necessary**: clarify first so the worker's output is good and
the review stays light; skip it and you pay Haiku *plus* a full Opus repair.

---

## Gap 2 — Repetition (n=3), to separate signal from noise

Same Django investigation, 3 runs per model.

| Model | Tokens (3 runs) | Mean | Spread | Cost (mean) |
|---|---|---|---|---|
| Haiku | 25.7k / 28.6k / 26.1k | 26,784 | ±5% | $0.0375 |
| Opus | 34.9k / 34.6k / 33.9k | 34,454 | ±1.5% | $0.2412 |

**Cost saving holds: 84.4% (mean), tight band** — the single-run 83.8% was not a fluke.

**But quality is noisier than n=1 implied:**
- Q3 (signals=10): Haiku **8/10/10** (one miss), Opus 10/10/10
- Q4 (commands=26): Haiku 26/26/26, **Opus 26/26/0** (one run gave up after a glob miss)
- Q5 (imports=36): Haiku 36/**39/39**, Opus 36/36/36
- Q1 (Field count): both drift (Haiku 45–48, Opus 35–36) — the metric itself is ill-defined

→ "Equal quality" is approximately true, but Haiku has **modestly higher error variance**;
Opus is steadier yet not flawless. n=1 hid this.

---

## Gap 3 — Sonnet in the matrix + a real debugging task

### 3a. Model matrix on the CLEAR-spec "orders" build (independent judge)

| Model | Tokens | Cost | Judge |
|---|---|---|---|
| Haiku | 47,818 | $0.067 | **12/12** |
| Sonnet | 41,688 | $0.175 | **12/12** |
| Opus | 48,090 | $0.337 | **12/12** |

All three pass equally on a clear spec → **Haiku is the rational choice; Sonnet/Opus add
2.6×–5× cost for no quality gain here.**

### 3b. Debugging a localized bug (injected: cancel-idempotency guard removed)

A failing test points straight at `cancel_order`; fix = re-add the guard.

| Model | Tokens | Cost | Fixed? |
|---|---|---|---|
| Haiku | 32,351 | $0.045 | yes |
| Sonnet | 28,060 | $0.118 | yes |
| Opus | 34,714 | $0.243 | yes |

**All three fixed it** — a well-localized bug does NOT reveal a reasoning gap; Haiku
handles it at 1/5 the cost. The hypothesis "reasoning models pull ahead on debugging"
would need a *subtle, non-localized* bug to show divergence; this one was too easy. (An
honest null result — the debugging-advantage claim remains untested for hard bugs.)

---

## What changed in our conclusions

1. **Cost saving on clear work is robust** (n=3, ~84%) — confirmed, not a fluke.
2. **The orchestrator pipeline is only cheap when the worker succeeds.** On vague work it
   costs *more* than all-Opus. → disambiguation is economically load-bearing, not polish.
3. **Quality parity is approximate**, with Haiku showing higher error variance — so the
   review step (Gap 1) earns its keep specifically as a *quality* guard, even though it
   isn't free.
4. **Sonnet adds nothing on clear bounded work** (same 12/12 as Haiku, higher cost) —
   its niche would be mid-complexity/ambiguity, still untested.
5. **Localized debugging shows no reasoning gap** — cheap models suffice; hard-bug
   debugging remains the open question.
