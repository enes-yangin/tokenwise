# tokenwise

**Maximum quality per token.** A Claude Code plugin that makes the agent stop wasting
tokens — without ever cutting correctness, validation, or security.

It bundles a persistent *lean-agent* mode with four focused workflow skills. The mode
is always on (via a SessionStart hook); the skills trigger when their work shows up.

The lean-agent mode, `plan-critique`, and `git-commit` are language-agnostic. `tdd` and
`py-debug` are Python-specific (pytest-based) — in a non-Python project those two simply
won't trigger; the rest of the plugin still applies.

## The idea

Quality-per-token = (correct, complete result) ÷ (tokens read + tokens generated +
tokens burned re-doing work). Four levers push that ratio up:

1. **Recall, don't re-derive** — use context / memory / `RULES.md` before re-reading or re-asking.
2. **Read surgically** — targeted Read, Grep/Glob, Explore subagents; never re-read.
3. **Generate lean** — recommendation over survey, no narration, minimum code that works.
4. **Avoid rework** — understand before changing, gather evidence before fixing, test early.

A **"never cut" band** protects what matters: understanding the problem, input validation
at trust boundaries, error handling, security, accessibility, and anything you explicitly
asked for. Lean means less waste, not a flimsier result.

## What's inside

| Component | Type | What it does |
|-----------|------|--------------|
| `tokenwise` | persistent mode | The four levers, enforced every response. `/tokenwise lite\|full\|off`. |
| `plan-critique` | skill | Plan → pre-mortem (find & solve problems up front) → red-team through personas → synthesize, before executing risky work. |
| `py-debug` | skill | Root-cause debugging protocol for Python (pytest, FastAPI, Django, Flask) — evidence before edits. |
| `tdd` | skill | Red → Green → Refactor test-first loop for pytest. |
| `git-commit` | skill | Atomic commits + branch hygiene + conventional messages. |
| RULES.md hook | hook | Auto-loads your project's `RULES.md` every session, so conventions never need re-explaining. |

---

## Installation — step by step

### Prerequisites

- Claude Code CLI, with the plugin system available (`/plugin` command works).
- `node` on your `PATH`. The hooks are Node scripts; if `node` isn't found, the
  Windows launch command (`if (Get-Command node ...)`) silently no-ops and tokenwise
  never activates — no error, it just won't turn on. Check with `node --version`
  before installing.
- This `tokenwise/` directory, either cloned from its repo or copied somewhere on
  disk. Note its absolute path — you'll need it below.

### Option A — the `/plugin` slash commands (recommended)

Run these two commands inside a Claude Code session:

```
/plugin marketplace add /absolute/path/to/tokenwise
```
**What this does:** registers `tokenwise/.claude-plugin/marketplace.json` as a known
plugin source (a "marketplace") under the name declared inside that file (`tokenwise`).
This alone does not install anything — it just tells Claude Code *where* the plugin
lives, the same way `apt-add-repository` doesn't install a package by itself.

```
/plugin install tokenwise@tokenwise
```
**What this does:** installs the plugin named `tokenwise` from the marketplace named
`tokenwise` (the `plugin@marketplace` syntax — the two names happen to match here
because this project defines one plugin per marketplace). This copies the plugin's
metadata into Claude Code's plugin registry and enables it for your user.

After both commands, **restart the session** (fully quit and reopen, not `/clear`) so
the `SessionStart` hook registration takes effect. You'll see a `TOKENWISE MODE ACTIVE`
block injected into context on the next start — that's your confirmation it's live.

### Option B — edit `settings.json` directly

If you'd rather configure this via file edits (e.g. scripting a team-wide setup),
add to `~/.claude/settings.json` (user-wide) or `.claude/settings.json` (this project
only):

```json
{
  "extraKnownMarketplaces": {
    "tokenwise": {
      "source": { "source": "directory", "path": "/absolute/path/to/tokenwise" }
    }
  },
  "enabledPlugins": {
    "tokenwise@tokenwise": true
  }
}
```
**What each field does:**
- `extraKnownMarketplaces.tokenwise.source` — same effect as `/plugin marketplace add`:
  registers a local-directory source under the name `tokenwise`. `source: "directory"`
  means "read `.claude-plugin/marketplace.json` directly from this path" — no network
  fetch, no git clone, just the folder on disk.
- `enabledPlugins["tokenwise@tokenwise"]` — same effect as `/plugin install`: turns the
  plugin on for this settings scope.

This is exactly what Option A does under the hood, minus the interactive round-trip —
useful if you're provisioning multiple machines or don't have an interactive session
to run slash commands in. Restart the session afterward, same as Option A.

### Verifying the install worked

1. Start a **new** session in the plugin's scope.
2. Check the skill list (or ask "what skills do you have") — you should see
   `tokenwise:tokenwise`, `tokenwise:plan-critique`, `tokenwise:py-debug`, `tokenwise:tdd`,
   `tokenwise:git-commit` — the `tokenwise:` prefix means they're coming from the plugin,
   not a standalone copy.
3. The first assistant turn should carry hidden `TOKENWISE MODE ACTIVE — level: full`
   context (visible if your client surfaces SessionStart hook output, or inferable from
   behavior — lean answers, no narration, surgical reads).

### Avoid double-registered skills

If you used any of `tokenwise`, `plan-critique`, `py-debug`, `tdd`, or `git-commit` as
**standalone** skills before installing this plugin (i.e. copied under
`~/.claude/skills/<name>/` directly, not through the plugin system), remove those
standalone copies once the plugin is installed — otherwise the same skill name is
registered twice, from two different sources, and it's undefined which one the harness
picks.

```
rm -rf ~/.claude/skills/{tokenwise,plan-critique,py-debug,tdd,git-commit}
```
Only run this **after** confirming (see above) that the plugin versions are actually
active — deleting the standalone copies first, then finding the plugin didn't register,
leaves you with neither.

---

## Usage — every command explained

| Command / trigger | What it does |
|---|---|
| `/tokenwise full` | Switches to **full** intensity (the default): maximally lean — recommendation-only, near-zero narration, minimum diffs, surgical reads. Best for well-specified tasks where you want the result, not the commentary. Takes effect **immediately**, mid-session (not just on next restart). |
| `/tokenwise lite` | Switches to **lite** intensity: same four levers, but conversational — brief context and a sentence of reasoning are allowed. Best for exploration, pairing, or ambiguous tasks where a little narration helps you both stay aligned. Also takes effect immediately. |
| `/tokenwise off` | Turns tokenwise off entirely — no ruleset injected, normal unconstrained behavior. This is **persisted**: it survives `/compact`, `/clear`, and session restarts (until you turn it back on), it does not silently re-enable itself. |
| "stop tokenwise" (typed in a sentence) | Same as `/tokenwise off` — an alternate phrasing some people reach for instead of the slash command. Deliberately requires the literal word "tokenwise" so it doesn't collide with unrelated phrases (a bare "normal mode" used to false-trigger this on any Vim-related conversation — fixed). |
| `TOKENWISE_MODE` environment variable (`lite`/`full`/`off`) | Sets the **starting default** for a machine/session that has never run a `/tokenwise ...` command yet. Once you've explicitly set a mode via command, that persisted choice always wins over the env var on every subsequent session — the env var is a fallback default, not a hard override. |
| Dropping a `RULES.md` at your project root | Auto-loaded into context at the start of every session (capped at 6000 chars; longer files are truncated with a notice, so trim it if you hit that). Means you never re-type project conventions. Get started with: `cp /path/to/tokenwise/RULES.template.md ./RULES.md`, then fill in the sections and delete the prompts you didn't need. |
| Just working normally | The four workflow skills trigger **on their own**, no command needed: a Python traceback or failing test pulls in `py-debug`; implementing new behavior pulls in `tdd`; starting a risky/ambiguous task pulls in `plan-critique`; committing pulls in `git-commit`. You only reach for `/tokenwise ...` to change the *lean-agent mode*, not to invoke these — they invoke themselves. |

### A worked example

```
/tokenwise lite
```
You're about to pair on an ambiguous refactor and want some narration along the way.
Immediately, the injected ruleset switches from "full" (near-zero commentary) to "lite"
(brief reasoning allowed) — for the rest of this session, or until you switch again.

```
stop tokenwise
```
You want completely unconstrained behavior for one task (say, a long free-form design
discussion where token efficiency isn't the point). This turns it off and it **stays**
off — including through `/compact` — until you explicitly turn it back on.

---

## Benchmark: does it actually work?

Rather than assert the four levers save tokens, we measured them. **Method:** the same
Sonnet model, the same task, run twice — once with the real tokenwise "full" ruleset
(the exact text the SessionStart hook injects) prepended to the prompt, once with no
extra instruction at all. Both implementations were graded by the same **independent
12-test judge suite** they never saw (`benchmark_heavy/judge_orders.py`), covering 7
hidden edge cases (atomic stock deduction, price snapshotting, cancel idempotency,
money-as-integer-cents, referential integrity, validation, 404s).

Task: add an "orders" resource to an existing 5-layer FastAPI codebase, from a clear,
fully-specified spec (`benchmark_heavy/SPEC_FEATURE.md`).

| Run | Tokens | Tool calls | Duration | Independent judge |
|---|---:|---:|---:|:---:|
| **tokenwise ON** (`tw_on`) | 51,950 | 21 | 108 s | **12/12** |
| **tokenwise OFF** (`tw_off`) | 48,859 | 25 | 91 s | **12/12** |

At $3/$15 per M (Sonnet, June 2026, blended ~$4.2/M): ON cost **$0.218**, OFF cost
**$0.205** — ON was **6.3% more expensive**, not less, at identical quality.

### Honest interpretation

On this task, **tokenwise's explicit ruleset did not reduce token count** — it used
slightly more tokens for the same result, with fewer but presumably larger tool calls.
This matches a finding already established in the sibling `/heavy`+`/route` project in
this repo (`../README.md`): **re-instructing a strong model to do things it already does
by default buys ~0 savings, and can add small overhead.** Sonnet already reads
surgically, batches calls, and avoids narration without being told to — telling it again
doesn't compound.

This single run is **n=1** and should be read as a data point, not a verdict — the rigor
work in the sibling project found real quality/cost variance even at n=3 on nominally
identical runs. It does NOT test the levers most likely to actually pay off:

- **Lever 1 (recall, don't re-derive) and the RULES.md hook** — their value compounds
  across a *long, multi-turn* session (avoiding re-reads/re-explanations several times
  over), not a single short single-agent task like this one.
- **Lever 4 (avoid rework)** — its payoff is on *ambiguous or error-prone* work, where
  the alternative is discovering a wrong turn late and re-doing it. This benchmark used
  a clear, fully-specified spec — exactly the condition where rework was unlikely either
  way, so there was nothing for this lever to prevent.

**Bottom line:** on a strong model doing a short, well-specified task, tokenwise is
roughly cost-neutral (a few % either way) at equal quality — it is not a magic token
reducer here. Its claimed value was hypothesized to concentrate in conditions this first
run didn't create: ambiguous/risky work (rework avoidance) and long sessions
(recall/RULES.md). The first of those two is now measured below.

### Second run — does it help on an AMBIGUOUS spec?

Same method, same model (Sonnet), same independent 12-test judge — but this time the
spec (`benchmark_heavy/SPEC_VAGUE.md`) leaves the edge cases **unstated**: it says what
endpoints to build, not the hidden rules (atomic stock, duplicate-line aggregation,
referential integrity) the judge actually checks. This is exactly the condition where
tokenwise's lever 4 ("avoid rework — gather evidence, don't guess") is supposed to earn
its keep: it can't prevent an ambiguous spec from being ambiguous, but it should push the
model to notice and handle risk it would otherwise skip past.

| Run | Tokens | Independent judge | Notes |
|---|---:|:---:|---|
| **tokenwise ON** (`tw_vague_on`) | 49,309 | **10/12** (11/12 excl. artefact) | caught duplicate-line stock aggregation; referential-integrity check exists but crashes uncaught (raw 500) |
| **tokenwise OFF** (`tw_vague_off`) | 48,905 | **9/12** (10/12 excl. artefact) | missed duplicate-line aggregation entirely (409 case returns 201); referential integrity not implemented at all (delete silently succeeds, 204) |

(One failure in both runs — `status` string "created" vs the judge's expected
"pending" — is a spec-wording artefact, not a reasoning gap: the vague spec never states
the status value. Excluded from the count above.)

**This is the first measurable win.** ON caught one more hidden edge case than OFF
(duplicate-line stock aggregation) at essentially the same token cost (+0.8%). The
*quality* of the shared failure also differs in ON's favor: OFF's referential-integrity
gap is a silent data-corruption bug (delete succeeds, 204, no protection at all); ON's is
an ugly unhandled crash (500) but the underlying protection — a DB foreign-key
constraint — actually exists, just isn't translated into a clean error. Neither is fully
correct, but "protection exists and is mishandled" is a smaller defect than "no
protection at all."

**Honest limits of this result:** n=1 per side, one task, one model. The gap (1 of 12
tests) is real but small, and the earlier rigor work in the sibling project showed
quality variance of this size can occur between runs even with no intervention at all —
this is suggestive, not conclusive, evidence that lever 4 helps on ambiguous work. What
it does rule out: tokenwise is not free — it cost essentially the same tokens here as in
the clear-spec run, so any quality gain is not bought by spending more.

Long-session recall/RULES.md value remains unmeasured — it needs a genuinely multi-turn
or multi-session task, which a single subagent run can't faithfully simulate.

---

## Testing the hooks

`hooks/test-hooks.js` is a dependency-free smoke test for the mode-persistence logic
(off survives restart, flag beats env, mid-session mode switches actually change
behavior). Run it after touching either hook:

```
node hooks/test-hooks.js
```
**What this does:** spins up temporary, isolated `CLAUDE_CONFIG_DIR` sandboxes and
invokes `tokenwise-activate.js` / `tokenwise-mode-tracker.js` exactly as Claude Code
would (JSON on stdin, JSON on stdout), asserting on the output — no mocking, the real
scripts run. All 8 cases should print `ok`.

## Layout

```
tokenwise/
├── .claude-plugin/{plugin.json, marketplace.json}
├── hooks/
│   ├── tokenwise-hooks.json           (hook registration)
│   ├── tokenwise-activate.js          (SessionStart)
│   ├── tokenwise-mode-tracker.js      (UserPromptSubmit)
│   ├── tokenwise-ruleset.js           (shared rule text, both hooks)
│   ├── tokenwise-flag.js              (shared per-project flag path)
│   └── test-hooks.js                 (smoke test, see above)
├── skills/
│   ├── tokenwise/SKILL.md
│   ├── plan-critique/SKILL.md
│   ├── py-debug/SKILL.md + references/{python-errors.md, frameworks.md}
│   ├── tdd/SKILL.md
│   └── git-commit/SKILL.md
└── RULES.template.md
```
