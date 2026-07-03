# Framework-specific debugging guidance

Read only the section for the framework in play. Each lists the traps specific to that
framework and the fastest way to confirm them — the generic protocol in SKILL.md still
applies, this is the framework-shaped detail for Phase 2–4.

## Contents
- [pytest](#pytest)
- [FastAPI](#fastapi)
- [Django](#django)
- [Flask](#flask)

---

<a name="pytest"></a>
## pytest

**Run it tight**
- `pytest path/to/test.py::test_name -x -vv` — one test, stop on first failure, full
  assertion diff. `-vv` is the highest-signal flag: it prints both sides of the
  failing assert instead of truncating.
- `pytest --lf` reruns last-failed; `--ff` runs failures first. `-k "expr"` selects by
  name substring.
- `pytest --pdb` drops into the debugger at the failure point with the frame live —
  inspect `p`/`pp` the actual values instead of guessing.
- `-s` lets prints/logging through (pytest captures stdout by default).

**Common traps**
- **Fixture scope / teardown**: a `scope="module"` or `session` fixture that holds
  mutable state leaks across tests → order-dependent failures. Confirm by running the
  test alone vs in the suite (see python-errors "Flaky").
- **conftest.py location**: fixtures are available to the directory tree they live in.
  A fixture "not found" usually means wrong `conftest.py` placement.
- **Parametrize**: a single failing case in `@pytest.mark.parametrize` is named in the
  test id (`test_x[case-3]`). Read the id to know *which* input failed; don't assume.
- **Mocking the wrong path**: patch where the name is *used*, not where it's defined —
  `mock.patch("mymodule.requests.get")` (the importing module), not
  `patch("requests.get")`, when `mymodule` did `import requests`.
- **assert rewriting off**: if you see bare `AssertionError` with no detail, the assert
  is inside a helper not collected by pytest, or in non-test code. Move the check or
  use `pytest.fail(msg)`.
- **Async tests**: need `pytest-asyncio` (and `@pytest.mark.asyncio` or `asyncio_mode`).
  A "coroutine never awaited" warning on a test means the plugin isn't active.

**Don't** chase a green bar by loosening the assertion. The assertion encodes the
intended behavior; weakening it hides the regression.

---

<a name="fastapi"></a>
## FastAPI

**Reproduce**: use `TestClient` (`from fastapi.testclient import TestClient`) to hit the
endpoint in a test — deterministic and fast, no live server. Inspect
`response.status_code` and `response.json()`.

**Common traps**
- **422 Unprocessable Entity**: Pydantic request validation rejected the body/query.
  The response body lists the exact field + reason — read it; it's precise. The bug is
  usually the model not matching the payload, not FastAPI.
- **Dependency injection (`Depends`)**: a dependency that raises turns into the error;
  trace which `Depends` ran. For tests, override with
  `app.dependency_overrides[dep] = fake` instead of patching internals.
- **500 with a traceback**: that's a normal Python exception in the handler — apply the
  generic protocol to the traceback. FastAPI just surfaced it.
- **async handler blocking**: a sync DB/HTTP call in an `async def` endpoint stalls the
  event loop (see python-errors "Async"). Symptom: fine in isolation, times out under
  load. Use async drivers or `def` (FastAPI runs sync handlers in a threadpool) or
  `asyncio.to_thread`.
- **Response model mismatch**: `response_model` filters/validates the return; a field
  silently dropped or a validation error on the way *out* points here.
- **Background tasks / startup events**: errors there don't surface on the request path;
  check the server log, not the response.

---

<a name="django"></a>
## Django

**Reproduce**: `python manage.py shell` to run the ORM/query interactively, or the test
runner (`python manage.py test app.tests.TestX.test_y`) / `pytest` with
`pytest-django`. `manage.py shell_plus --print-sql` (django-extensions) prints the SQL.

**Common traps**
- **`DoesNotExist` / `MultipleObjectsReturned`**: `.get()` found zero / more than one.
  Confirm the actual filter and the actual rows (`.filter(...).count()`); decide
  whether zero/many is legitimate (then use `.filter().first()` or handle it) or an
  upstream data bug.
- **N+1 queries / slowness**: accessing a related object in a loop fires a query each
  time. Confirm with `django-debug-toolbar` or `len(connection.queries)`; fix with
  `select_related` (FK) / `prefetch_related` (M2M/reverse).
- **Migrations**: `InconsistentMigrationHistory` / "table already exists" / a model
  change with no migration. Run `python manage.py makemigrations --check` and
  `showmigrations` to see state. Don't hand-edit the DB to match — generate/repair the
  migration so other environments stay consistent.
- **Settings / `DJANGO_SETTINGS_MODULE`**: `ImproperlyConfigured` usually means the
  wrong/absent settings module or accessing settings before setup. In tests, ensure the
  test settings are loaded.
- **Request lifecycle**: middleware order matters; an attribute "missing" on `request`
  often means the middleware that sets it runs after the one reading it.
- **Signals**: behavior you can't find in the view may be a `post_save`/`pre_delete`
  signal handler. Grep `@receiver` / `.connect(`.
- **QuerySet laziness**: a query doesn't hit the DB until iterated/evaluated; "it
  didn't run" may mean you never consumed the QuerySet.

---

<a name="flask"></a>
## Flask

**Reproduce**: `app.test_client()` for requests; `app.test_request_context()` to run
code that needs a request/app context in a test.

**Common traps**
- **"Working outside of application context" / "request context"**: accessing
  `current_app`, `g`, `request`, or `session` outside a request (background thread,
  CLI, module import time, a test without a context). Push the right context
  (`with app.app_context():` / `test_request_context()`), or pass the value explicitly
  instead of reaching for the global.
- **Blueprint registration / routing 404**: blueprint not registered, wrong
  `url_prefix`, or `url_for` with the wrong endpoint name (`blueprint.view`). Check
  `app.url_map` to see what's actually registered.
- **Extension init**: extensions initialized at import vs via `init_app(app)` in a
  factory; using the extension before `init_app` ran gives "not initialized" errors.
- **Debug vs production config**: `app.debug`/config flips behavior (error pages,
  reloader); a bug that only shows in one mode points at config.
- **Threading / globals**: `g` is per-request; storing cross-request state on it or on
  module globals causes leakage under concurrency.
