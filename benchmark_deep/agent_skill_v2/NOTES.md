# NOTES

## Plan
- Single main.py: FastAPI + stdlib sqlite3. `app` exported.
- DB path via env DB_PATH; default file. Tests use :memory: shared per-connection -> use per-app connection.
- Isolation: each TestClient builds fresh DB. Use env var DB_PATH=:memory: + new connection on startup. To allow multiple isolated clients in one process, build app via create_app() and main also calls it; tests can set env before import OR we re-init. Simplest: connection stored on app.state, created at import from DB_PATH env. Test sets DB_PATH=":memory:" before importing main -> one shared in-mem conn for that test session. For isolation per test, recreate schema/truncate in fixture.

## Decisions
- Use a single sqlite3 connection (check_same_thread=False), guarded; TestClient is sync single-thread.
- Money: ints only.
- Atomic stock: validate all items first (existence + stock), then apply in one transaction.
- Cancel idempotency: 409 if already cancelled; restock only on transition pending/paid -> cancelled.
- Delete product: 409 if referenced in any order_item.
- revenue-by-category: sum unit_price_cents*quantity for items in non-cancelled orders, grouped by product.category.

## Status
- [x] SPEC read
- [x] tests written
- [x] main.py
- [x] all pass
