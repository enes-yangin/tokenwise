---
name: py-debug
description: >-
  Systematic root-cause debugging protocol for Python projects (pytest, ruff,
  FastAPI, Django, Flask). Use this skill WHENEVER a Python error, failing test,
  traceback, or unexpected behavior shows up — e.g. "why is this test failing",
  "fix this AttributeError", "this endpoint returns 500", "my migration breaks",
  "this works locally but not in CI", or any moment you'd otherwise be tempted to
  guess at a fix. It forces evidence-gathering before code changes so you diagnose
  the real cause instead of patching symptoms. Trigger it even when the bug looks
  obvious — the protocol is cheap and catches wrong guesses early.
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - AskUserQuestion
---

# Python Debug Protocol

## Why this exists

The most expensive debugging failure is **confident guessing**: reading half a
traceback, pattern-matching to a plausible cause, editing code, and re-running to
"see if it works." When the guess is wrong you've now changed code for no reason,
possibly masked the real bug, and lost the original signal.

This protocol replaces guessing with a short evidence loop. Every step produces a
fact you can point to. You stop changing code until a hypothesis is **confirmed by
evidence**, not by plausibility. It costs a few extra minutes up front and saves
the much longer thrash of fixing the wrong thing.

Follow the phases in order. Don't skip ahead to a fix because the cause "looks
obvious" — the obvious cause is wrong often enough that the check is worth it.

## Phase 1 — Reproduce reliably

You cannot debug what you cannot trigger on demand. Before anything else, get a
single command that reproduces the failure every time.

- Capture the **exact** command (test invocation, request, script) and its **full**
  output — the complete traceback, not the last line.
- If the report is vague ("it's broken", "sometimes fails"), pin it down: which
  input, which environment, how often. Use `AskUserQuestion` if you genuinely
  can't reproduce and need the user to supply the trigger.
- For tests: `pytest path/to/test.py::test_name -x -vv` runs just the failing test
  with full assertion output. `pytest --lf` reruns last-failed.
- Note whether it's deterministic. A flaky failure is a different (harder) problem —
  see `references/python-errors.md` → "Flaky / non-deterministic".

If you can't reproduce, that is itself the finding. Don't fabricate a fix for a bug
you can't see — report what you tried and ask for the missing piece.

## Phase 2 — Read the traceback properly

Python tracebacks are precise; most "mysterious" bugs are just unread tracebacks.

- Read **bottom-up**: the last line is the exception type + message. That's the
  *what*. The frame directly above it is *where*.
- Find the **deepest frame inside our own code** (skip library frames). That line is
  usually where the wrong value or wrong call originates, even if the exception
  surfaces deeper in a library.
- Read the **actual values**: `pytest -vv` shows the full assertion diff; for live
  errors add `repr()` of the suspect variables. "It's None" vs "it's an empty dict"
  are different bugs.
- Run with `python -X dev` (or `PYTHONDEVMODE=1`) to surface ResourceWarnings and
  deprecations that often precede the real failure.

Match the exception signature against `references/python-errors.md` — it maps common
Python error types (ImportError/circular imports, AttributeError on None,
mutable-default-arg, async pitfalls, encoding, venv mismatches) to their usual root
causes and the fastest way to confirm each.

## Phase 3 — Form hypotheses before touching code

Write down **2–3 concrete hypotheses**, ranked by likelihood. A hypothesis names a
specific cause and predicts what you'd observe if it were true. "Something with the
database" is not a hypothesis; "the session is committed before the FK row exists,
so the insert violates the constraint" is.

Stating them first stops you from anchoring on the first idea and forces falsifiable
predictions you can actually test in Phase 4.

## Phase 4 — Confirm with evidence (no fixes yet)

Now gather facts to confirm or kill each hypothesis, **without editing program
logic**. Inspection only:

- **Read the source** around the deepest in-code frame. Often the bug is visible on
  re-reading with the exception in mind.
- **Inspect runtime state** — the highest-signal move. Drop a `breakpoint()` at the
  suspect line (or run `pytest --pdb` to break at the failure) and inspect actual
  values, types, and call args. pdb basics: `p expr`, `pp expr`, `w` (where), `u`/`d`
  (up/down frames), `l` (list source), `c` (continue).
- **Targeted logging** when pdb isn't practical (async, servers, CI): log `repr()` of
  the specific suspect values — not scattered "got here" prints.
- **Bisect** when the cause is unclear: shrink to a minimal reproduction, or use
  `git bisect` / `git log -p` on the relevant file to find the change that
  introduced it. A regression that "worked yesterday" almost always has a commit.

Confirm the hypothesis against a real observation. If all hypotheses are killed,
return to Phase 3 with what you learned — don't start editing hopefully.

## Phase 5 — Fix the root cause, not the symptom

Only after a confirmed diagnosis, change code.

- Fix the **cause**. Wrapping the failing line in `try/except`, adding an `if x is
  not None` guard, or `# type: ignore` usually hides the symptom while the real bug
  (why is it None?) remains. Ask: "if I deleted this line, would the root cause still
  produce a bug elsewhere?" If yes, you're patching a symptom.
- Make the **smallest** change that addresses the cause. Resist refactoring nearby
  code in the same pass — it muddies the verification signal.
- Match the surrounding code's style and idioms.

## Phase 6 — Verify

A fix is a new hypothesis ("this resolves it") and needs the same evidence standard.

- Rerun the **exact** Phase 1 reproduction. It must now pass.
- Run the surrounding tests for regressions: `pytest path/to/module/` (or the whole
  suite if the change is broad).
- Run `ruff check` on changed files to catch anything introduced.
- Confirm you fixed it for the **right reason** — that the observed behavior now
  matches your Phase 4 diagnosis, not that the symptom merely vanished.

## Phase 7 — Capture the learning

One or two lines: what the root cause actually was and how it was confirmed. This is
worth saving to project memory or a `learnings` note when the bug was non-obvious or
likely to recur — future-you debugging the same class of error will thank you.

## Framework-specific guidance

When the bug involves a framework, read the relevant section of
`references/frameworks.md` — it covers the traps specific to each:

- **pytest** — fixtures, parametrize, `conftest.py` scope, mocking, async tests.
- **FastAPI** — dependency injection, Pydantic validation, async request handling.
- **Django** — ORM query/migration issues, request lifecycle, settings, signals.
- **Flask** — application/request context errors, blueprints, extension setup.

## The one rule

If you're about to edit code and you cannot state the specific evidence that
confirmed the cause, stop. You're in Phase 5 without finishing Phase 4 — go back and
get the evidence first.
