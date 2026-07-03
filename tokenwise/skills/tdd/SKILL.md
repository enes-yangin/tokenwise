---
name: tdd
description: >-
  Test-driven development loop for Python (pytest): write a failing test first, make it
  pass with the minimum code, then refactor. Use this WHENEVER you're implementing new
  behavior, a bug fix that should stay fixed, or any change where "does it actually
  work" matters — e.g. "add this function", "implement this endpoint", "fix this bug
  and add a test", or when the user mentions TDD, test-first, or coverage. Writing the
  test first catches errors in seconds instead of in manual QA, which is the cheapest
  rework you'll ever do. Prefer this over writing code then bolting tests on after.
---

# TDD — test-first for Python

Write the test before the code. Not for ceremony — because a test written first turns a
vague request into an executable spec, and catches the error the moment it appears
instead of three steps later when it's expensive to trace. The cheapest bug is the one
your own test catches in two seconds.

The loop is **Red → Green → Refactor**. Do them in order; the order is the point.

## Phase Red — write a failing test first

Before any implementation, write a test that describes the behavior you want and watch
it fail.

- Name the behavior, not the function: `test_full_name_strips_extra_space`, not
  `test_full_name_1`. The name is documentation.
- One behavior per test. A test that asserts five things tells you little when it fails.
- **Run it and confirm it fails for the right reason** — a missing function or a wrong
  value, not a typo or import error in the test itself. A test that passes before you've
  written the code, or errors for the wrong reason, is testing nothing.
  `pytest path::test_name -x -vv`.

Why first: if you write code then a test, the test is shaped by the code you already
wrote and tends to confirm it rather than challenge it. The failing test first proves
the test can actually fail, and pins the spec before implementation bias creeps in.

## Phase Green — minimum code to pass

Write the **least** code that makes the test pass. Not the elegant general version —
the simplest thing that goes green. Resist building for requirements you don't have a
test for yet.

- Run the test; confirm green: `pytest path::test_name -x -vv`.
- If it's still red, you're debugging, not implementing — read the `-vv` diff, fix the
  actual gap. Don't add more code hopefully.

This restraint is the token-discipline payoff: you build exactly what's specified and
no more, and you never have untested code paths.

## Phase Refactor — clean up, tests stay green

Now that behavior is locked by a passing test, improve the code's shape — rename, dedupe,
extract — running the test after each step. The test is your safety net: if it goes red
during refactor, the last change broke something, revert and retry. Refactor the test
too if it got repetitive (but never loosen an assertion to make a refactor "work").

## Choosing what to test (intensity)

- **lite**: cover the happy path plus the one or two failure modes that matter. Good for
  straightforward functions and rapid iteration. Don't over-test trivial glue.
- **full**: happy path **plus edge cases** — empty/None input, boundaries (0, 1, max),
  malformed input at trust boundaries, error paths. Use `@pytest.mark.parametrize` to
  cover many inputs in one compact test rather than copy-pasting test bodies.

Match intensity to risk: a payment calculation deserves full edge coverage; a one-line
formatter does not. Lean means testing what can actually break, not testing everything.

## Bug-fix variant (regression test first)

For a bug fix, the failing test *is* the reproduction:
1. Write a test that reproduces the bug → it fails (Red), confirming you've captured the
   real defect.
2. Fix the root cause (see the `py-debug` skill if the cause isn't obvious) → test goes
   green.
3. The test stays in the suite forever, so the bug can't silently return.

This is the highest-value test you can write — it's pinned to a bug that actually
happened.

## pytest quick reference

- `pytest path::test -x -vv` — one test, stop on fail, full assertion diff (highest signal).
- `pytest --lf` — rerun only last-failed; `--ff` — failures first.
- `pytest -k "name_substr"` — select by name.
- `@pytest.mark.parametrize("inp,expected", [...])` — table-driven cases, one body.
- Fixtures for shared setup; mind scope (`function` default) so state doesn't leak.
- Async: `pytest-asyncio` + `@pytest.mark.asyncio`.

## The rhythm

One small Red → Green → Refactor cycle at a time, each a few minutes. Don't write ten
tests then ten implementations — the tight loop is what keeps the error cheap to find.
Run `ruff check` on touched files before calling it done.

## The one rule

If you're about to write implementation code and there is no failing test demanding it,
stop and write the test first. Code without a test that drove it is code whose behavior
nobody pinned down.
