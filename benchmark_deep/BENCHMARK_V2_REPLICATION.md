# Replication — Skill vs No-Skill, current `/heavy` content

The original deep benchmark (`BENCHMARK_RESULTS.md`, `BENCHMARK_HAIKU_vs_OPUS.md`) used
an older "tokenwise+tdd+py-debug" prompt, written before `/heavy` was revised (delta
re-scoped to cost-routing + acceptance-check + external memory + cache discipline).
Re-ran with the **current `/heavy` skill text verbatim**, same pinned `SPEC.md`, same
independent judge suite (17 tests / 7 edge cases), agents never saw the judge.

## Results (v2, current `/heavy`)

| Run | Tokens | Cost | Judge | Note |
|---|---:|---:|:---:|---|
| Opus Skill | 42,820 | $0.300 | **16/17** | missed duplicate-line stock aggregation |
| Opus No-Skill | 43,574 | $0.305 | **17/17** | hit + self-fixed a threading bug |
| Haiku Skill | 47,564 | $0.067 | **16/17** | same miss as Opus-skill; DB isolation handled correctly (singleton) |
| Haiku No-Skill | 47,018 | $0.066 | **3/17** | classic `:memory:`-per-request isolation bug |

## v1 → v2 comparison

| Run | v1 judge | v2 judge | v1 tokens | v2 tokens |
|---|:---:|:---:|---:|---:|
| Opus Skill | 17/17 | 16/17 | 42,395 | 42,820 |
| Opus No-Skill | 17/17 | 17/17 | 40,815 | 43,574 |
| Haiku Skill | 6/17 | 16/17 | 55,597 | 47,564 |
| Haiku No-Skill | 16/17 | 3/17 | 53,801 | 47,018 |

## What changed, what didn't

**Token/cost: stable.** Opus ~42-44k both runs; Haiku ~47-56k both runs. The skill
rewrite (shorter, more cost-focused) didn't meaningfully move token count on this task —
consistent with the earlier finding that re-instructing/encoding discipline doesn't cut
tokens on a strong-enough model.

**Quality: the SAME bug categories recur, but on DIFFERENT runs.** This is the important
result:
- The `:memory:`-per-request isolation bug hit **Skill-Haiku in v1** and **No-Skill-Haiku
  in v2** — opposite assignment. It is not a property of "skill vs no-skill"; it's a
  coin-flip mistake either Haiku run can make.
- The duplicate-line stock-aggregation miss hit **both Skill runs in v2** (Opus AND
  Haiku) but neither No-Skill run. Root cause: `SPEC.md`'s edge case #1 text says "if one
  line is insufficient" — it does not spell out "if the same product appears on two
  lines, sum them first." The skill's acceptance-check discipline only protects against
  edge cases the agent thinks to enumerate; if the agent's own reading of an underspecified
  spec misses a sub-case, writing the test first does not rescue it. No-skill Opus simply
  implemented duplicate-summing as a natural by-product of how it wrote the stock loop —
  lucky, not principled.

**Conclusion: this benchmark is high-variance and inconclusive on skill-vs-no-skill at
n=1 per cell.** Across two replications (4 runs each), the win flips between Skill and
No-Skill on both models. The honest reading is the same as the rigor pass's finding on
the Django investigation: **n=1 is not enough to call winners on quality; only the COST
gap (Haiku ~5x cheaper) replicates reliably.**

## Bottom line

1. **Cost gap reproduces exactly**: Haiku ≈ 1/4–1/5 of Opus cost in both v1 and v2,
   regardless of skill.
2. **Quality is noisy at n=1** on both models — different bugs surface on different runs,
   not tied to skill/no-skill in a stable way.
3. **Disambiguation has a limit**: even an acceptance-check discipline only catches edge
   cases the agent itself enumerates from the spec. An underspecified spec sentence
   ("if a line is insufficient") can hide a sub-case ("if the same product is split
   across two lines") that bites Opus and Haiku alike, skill or not.
4. This reinforces (not contradicts) the project's core finding: route by **cost**, not
   by assuming a skill prompt buys quality on a single run — quality differences this
   small need n≥3 to read, exactly as the rigor pass showed on Django.
