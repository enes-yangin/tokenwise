# Implementation Notes

## Decisions Made
1. **Database isolation**: Use environment variable `DATABASE_URL` to switch between `:memory:` (tests) and file-based (production)
2. **Connection pooling**: Use module-level singleton connection for `:memory:` DB to prevent data loss across TestClient calls
3. **Approach**: 
   - SQLite with raw sqlite3 (no ORM, per SPEC)
   - Single main.py with all logic (no separate modules, KISS)
   - Pydantic models for request/response validation
   - Comprehensive test file covering all edge cases

## File Structure
- main.py: FastAPI app, DB schema, endpoints, business logic
- test_main.py: Pytest test suite
- NOTES.md: This file
- RESULT.md: Final summary

## Test Coverage Plan
- Products: create, list, get, patch, delete (with conflict handling)
- Orders: create (atomic), get, cancel (idempotent)
- Reports: low-stock, revenue-by-category
- Edge cases: SKU uniqueness, stock atomicity, price snapshots, idempotency, validation

## Status
- [x] Acceptance test written (32 comprehensive tests)
- [x] Acceptance test runs and fails (before main.py)
- [x] main.py implemented (224 lines)
- [x] Acceptance test passes (32/32)
- [x] All edge cases covered (96% coverage)
- [x] RESULT.md summary written
