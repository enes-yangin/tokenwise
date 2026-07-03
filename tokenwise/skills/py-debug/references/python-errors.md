# Python error signatures → root cause → fastest confirmation

A lookup table for Phase 2 of the protocol. Find the exception you're seeing, read
the *usual* cause, then run the **confirm** step — a cheap observation that proves or
kills the hypothesis before you change code. The signature is rarely the bug; it's a
pointer to where the wrong value came from.

## Contents
- [ImportError / ModuleNotFoundError / circular import](#import)
- [AttributeError: 'NoneType' object has no attribute ...](#none)
- [KeyError / IndexError](#keyindex)
- [TypeError](#type)
- [Mutable default argument](#mutable-default)
- [UnboundLocalError / closure surprises](#unbound)
- [Async pitfalls](#async)
- [UnicodeDecodeError / encoding](#encoding)
- ["Works locally, fails in CI" / venv mismatch](#venv)
- [Flaky / non-deterministic failures](#flaky)
- [RecursionError](#recursion)

---

<a name="import"></a>
## ImportError / ModuleNotFoundError / circular import

**Usual causes**
- Wrong interpreter/venv — the package is installed somewhere else (see [venv](#venv)).
- Circular import: module A imports B at top level while B imports A. The symptom is
  often `ImportError: cannot import name 'X' from partially initialized module` or an
  `AttributeError` on a half-built module.
- Package not installed in editable mode; `src/` layout without install.
- Shadowing: a local file named like a stdlib/third-party module (`random.py`,
  `email.py`) wins on `sys.path`.

**Confirm**
- `python -c "import sys; print(sys.executable)"` and `python -m pip show <pkg>` — is
  it the interpreter you think, and is the package there?
- For circular imports, read the traceback: the two modules in the cycle are named in
  the frames. Confirm by checking whether the import that fails is at module top level
  vs inside a function.
- Shadowing: `python -c "import <mod>; print(<mod>.__file__)"` — does it point at your
  own file by accident?

**Root-cause fix, not symptom**
- Circular import: move the import inside the function that needs it (deferred import),
  or extract the shared piece into a third module both can import. Don't paper over it
  with `try/except ImportError`.

---

<a name="none"></a>
## AttributeError: 'NoneType' object has no attribute '...'

The single most common Python bug. The real question is **why is it None** — the
attribute access is just where it surfaced.

**Usual causes**
- A function that returns a value on some paths and falls off the end (returns `None`)
  on others.
- `.get()` on a dict for a missing key; a query/ORM call that found nothing
  (`.first()`, `.find_one()` returning `None`).
- An in-place method used as if it returned a value: `x = mylist.sort()` /
  `s = s.strip` (forgot `()`) / `d = d.update(...)` — these return `None`.
- Reassigning a name to the result of a `print()` or a void call.

**Confirm**
- Don't guard yet. Find the assignment that produced the None and print its source:
  `breakpoint()` one line above the failing access, then `p the_variable` and walk
  *backwards* to where it was set.
- Grep the function being called: does every branch `return`?

**Root-cause fix**
- Fix the producer (make the function return on all paths, handle the empty-query
  case meaningfully). Adding `if x is not None:` at the access site usually just hides
  the bug — the None still means something upstream went wrong.

---

<a name="keyindex"></a>
## KeyError / IndexError

**Usual causes**
- Off-by-one or empty sequence (`lst[0]` on `[]`).
- Assuming a key exists in a dict built from external/variable data.
- Iterating and mutating the same collection.

**Confirm**
- `pytest -vv` prints the actual key/index and the actual container. Read the real
  contents — is the key spelled differently, is the list empty, is it the right object?
- For "sometimes" failures, log `len()` and `repr()` of the container right before access.

**Root-cause fix**
- If the key/index legitimately may be absent, that's a real branch — handle it
  (`.get(k, default)`, length check). If it should always be present, the bug is
  upstream where the container was built; fix there.

---

<a name="type"></a>
## TypeError

**Usual causes**
- `argument of type 'NoneType'` / `unsupported operand 'int' + 'str'`: a value isn't
  the type you assumed — often a None or a stringified number from JSON/env/CSV.
- `missing N required positional arguments` / `takes N but M given`: signature drift,
  or calling a method without `self` context, or forgetting `()` vs passing the
  function itself.
- `'X' object is not callable`: shadowed a function name with a value, or called a
  module/class instance.

**Confirm**
- `pytest -vv`, or `print(type(x), repr(x))` on the operands. The *type* is the clue:
  a number that's actually a `str` points at a missing `int()`/parse at the boundary.

**Root-cause fix**
- Convert/validate at the **trust boundary** (where data enters: request parsing, env
  read, file load), not at the point of use scattered everywhere.

---

<a name="mutable-default"></a>
## Mutable default argument (`def f(x, items=[])`)

**Symptom**: a list/dict/set "remembers" values across calls; state leaks between
unrelated invocations.

**Cause**: the default is evaluated **once** at function definition, so every call
without the arg shares the same object.

**Confirm**: call the function twice without the arg; the second call sees the first
call's mutations.

**Fix**: `def f(x, items=None): if items is None: items = []`.

---

<a name="unbound"></a>
## UnboundLocalError / closure surprises

**Usual causes**
- Assigning to a name anywhere in a function makes it local for the *whole* function;
  reading it before assignment (or intending the outer/global one) raises
  `UnboundLocalError`.
- Late-binding closures in loops: `[lambda: i for i in range(3)]` all see the final `i`.

**Confirm**: read the function for an assignment to the same name; for closures, check
whether the captured variable changes after the closure is created.

**Fix**: use `nonlocal`/`global` deliberately, or rename; for loop closures bind via a
default arg (`lambda i=i: i`) or a factory function.

---

<a name="async"></a>
## Async pitfalls

**Usual causes**
- `RuntimeWarning: coroutine '...' was never awaited` — you called an `async def`
  without `await` (or passed it where a value was expected). The coroutine never ran.
- Blocking call (sync DB driver, `requests`, `time.sleep`, heavy CPU) inside an async
  handler freezes the event loop → timeouts, "slow under load".
- Mixing event loops / calling `asyncio.run()` inside an already-running loop.

**Confirm**
- Run with `python -X dev` to surface the "never awaited" warning with the exact line.
- For loop-blocking, search the async path for sync I/O libraries; if a request hangs
  only under concurrency, that's the tell.

**Root-cause fix**
- `await` the coroutine. Replace blocking I/O with async equivalents, or offload to
  `asyncio.to_thread(...)` / a thread pool. Don't wrap in a bare `try/except` to
  silence the warning — that hides un-run code.

---

<a name="encoding"></a>
## UnicodeDecodeError / encoding

**Usual causes**
- Reading a non-UTF-8 (or binary) file with text mode and the default encoding.
- Platform default differs (Windows cp1252 vs Linux utf-8) — classic "works on my
  machine".

**Confirm**: which byte at which position (the error states it); `file <path>` or read
the first bytes in binary mode to see the real encoding/BOM.

**Fix**: open with an explicit `encoding=` (usually `"utf-8"`); for unknown/mixed data,
decide a policy (`errors="replace"` only if lossiness is acceptable). Set encoding at
the boundary, don't sprinkle decode/encode through the code.

---

<a name="venv"></a>
## "Works locally, fails in CI" / venv & interpreter mismatch

**Usual causes**
- Different Python version or different installed package versions between environments.
- Dependency not pinned; CI resolves a newer (breaking) version.
- Relying on a package installed globally/locally but missing from
  `requirements.txt` / `pyproject.toml`.
- Environment variables / config present locally but absent in CI.
- Path/cwd assumptions, or test order/isolation differences.

**Confirm** (make the environments comparable)
- `python --version`, `pip freeze` in both; diff them.
- Reproduce CI's install from a clean venv: `python -m venv .venv && pip install -r
  requirements.txt` (or the project's exact install command).
- Check the CI config for env vars the code reads.

**Root-cause fix**: pin versions, add the missing dependency to the manifest, make
config explicit. A green run that depends on an unpinned transitive dep is a
time-bomb, not a fix.

---

<a name="flaky"></a>
## Flaky / non-deterministic failures

Harder class: the failure is real but doesn't reproduce every time. Stabilize *first*,
then debug — you can't confirm a fix you can't trigger.

**Usual causes**
- **Order dependence**: tests share state (module globals, DB rows, files, a cached
  singleton); passing alone but failing in suite, or vice versa.
- **Time**: `datetime.now()`, timezones, timeouts, DST, sub-second assumptions.
- **Randomness**: unseeded `random`/UUIDs/hash ordering (`PYTHONHASHSEED`).
- **Concurrency**: races, shared mutable state across threads/async tasks.
- **External**: network, real services, filesystem timing.

**Confirm / stabilize**
- Run the single test in isolation vs in the suite: `pytest path::test` vs full run.
  Different result ⇒ order/shared-state dependence.
- `pytest -p no:randomly` or fix the seed to check ordering effects; `pytest --lf`,
  and rerun N times to measure the failure rate.
- Freeze time (inject a clock / `freezegun`), seed RNG, mock the external dependency.

**Root-cause fix**: remove the shared mutable state or isolate it per test (fixtures
with proper scope/teardown); inject time and randomness as dependencies so they're
controllable. Re-running until green is not a fix.

---

<a name="recursion"></a>
## RecursionError: maximum recursion depth exceeded

**Usual causes**: missing/incorrect base case; a property/`__getattr__`/`__eq__` that
calls itself; mutual recursion with no termination.

**Confirm**: read the repeated frames in the traceback — they name the cycle. Check the
base-case condition with the actual argument values (`breakpoint()` at function entry).

**Fix**: correct the base case or the recursive step. Raising
`sys.setrecursionlimit` is almost always treating the symptom — only legitimate for
genuinely deep-but-finite recursion, and even then iteration is usually better.
