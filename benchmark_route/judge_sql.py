"""Bağımsız jüri — SQL. Agent'lar görmez.
Kullanım: JUDGE_TARGET=<agent_dir> python judge_sql.py
Şema+seed'i sql_shared'dan yükler, agent'ın q1..q4.sql'ini koşup beklenen
satır listeleriyle birebir karşılaştırır (sıra dahil)."""
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.join(HERE, "sql_shared")
TARGET = os.environ["JUDGE_TARGET"]

EXPECTED = {
    "q1": [("Alice", 600), ("Carol", 600), ("Dave", 300)],
    "q2": [("TR", 2), ("US", 2)],
    "q3": [("widget", 6), ("gadget", 3)],
    "q4": [("Bob",)],
}


def load_db():
    conn = sqlite3.connect(":memory:")
    with open(os.path.join(SHARED, "schema.sql")) as f:
        conn.executescript(f.read())
    with open(os.path.join(SHARED, "seed.sql")) as f:
        conn.executescript(f.read())
    return conn


results = []
for q, expected in EXPECTED.items():
    path = os.path.join(TARGET, f"{q}.sql")
    try:
        with open(path) as f:
            sql = f.read()
        conn = load_db()
        rows = [tuple(r) for r in conn.execute(sql).fetchall()]
        conn.close()
        ok = rows == expected
        results.append((q, ok, "" if ok else f"got {rows}, want {expected}"))
    except Exception as e:
        results.append((q, False, repr(e)))

passed = sum(1 for _, ok, _ in results if ok)
for q, ok, err in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {q}" + (f"  -> {err}" if not ok else ""))
print(f"SCORE: {passed}/{len(results)}")
