"""Bağımsız jüri — LRUCache. Agent'lar bu dosyayı görmez.
Kullanım: JUDGE_TARGET=<dir> python judge_lru.py
Sahte saat enjekte eder; her kural ayrı test, SCORE: x/10 basar."""
import os
import sys
import importlib.util

TARGET = os.environ["JUDGE_TARGET"]
spec = importlib.util.spec_from_file_location("lru_under_test", os.path.join(TARGET, "lru.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
LRUCache = mod.LRUCache


class Clock:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t
    def advance(self, d): self.t += d


results = []
def check(name, fn):
    try:
        fn()
        results.append((name, True, ""))
    except Exception as e:
        results.append((name, False, repr(e)))


def t_basic():
    c = LRUCache(2, ttl=100, now=Clock())
    c.put("a", 1)
    assert c.get("a") == 1

def t_miss():
    c = LRUCache(2, ttl=100, now=Clock())
    assert c.get("nope") is None

def t_lru_evict():
    c = LRUCache(2, ttl=100, now=Clock())
    c.put("a", 1); c.put("b", 2); c.put("c", 3)  # a en eski -> atılır
    assert c.get("a") is None
    assert c.get("b") == 2 and c.get("c") == 3

def t_get_protects():
    c = LRUCache(2, ttl=100, now=Clock())
    c.put("a", 1); c.put("b", 2)
    c.get("a")           # a MRU olur
    c.put("c", 3)        # b atılmalı, a değil
    assert c.get("a") == 1
    assert c.get("b") is None

def t_update_existing():
    c = LRUCache(2, ttl=100, now=Clock())
    c.put("a", 1); c.put("b", 2)
    c.put("a", 99)       # güncelle + MRU, kapasiteyi şişirme
    assert c.get("a") == 99
    assert len(c) == 2
    c.put("c", 3)        # b atılmalı (a MRU)
    assert c.get("b") is None and c.get("a") == 99

def t_ttl_expire():
    clk = Clock()
    c = LRUCache(2, ttl=100, now=clk)
    c.put("a", 1)
    clk.advance(100)
    assert c.get("a") is None

def t_ttl_within():
    clk = Clock()
    c = LRUCache(2, ttl=100, now=clk)
    c.put("a", 1)
    clk.advance(50)
    assert c.get("a") == 1

def t_len_excludes_expired():
    clk = Clock()
    c = LRUCache(5, ttl=100, now=clk)
    c.put("a", 1); c.put("b", 2)
    clk.advance(100)
    assert len(c) == 0

def t_capacity_zero():
    c = LRUCache(0, ttl=100, now=Clock())
    c.put("a", 1)
    assert c.get("a") is None
    assert len(c) == 0

def t_expired_frees_room():
    clk = Clock()
    c = LRUCache(2, ttl=100, now=clk)
    c.put("a", 1); c.put("b", 2)
    clk.advance(100)      # ikisi de süresi geçti
    c.put("c", 3)         # temizlik sonrası c rahatça girer
    assert c.get("c") == 3


for name, fn in [
    ("basic", t_basic), ("miss", t_miss), ("lru_evict", t_lru_evict),
    ("get_protects", t_get_protects), ("update_existing", t_update_existing),
    ("ttl_expire", t_ttl_expire), ("ttl_within", t_ttl_within),
    ("len_excludes_expired", t_len_excludes_expired),
    ("capacity_zero", t_capacity_zero), ("expired_frees_room", t_expired_frees_room),
]:
    check(name, fn)

passed = sum(1 for _, ok, _ in results if ok)
for name, ok, err in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  -> {err}" if not ok else ""))
print(f"SCORE: {passed}/{len(results)}")
