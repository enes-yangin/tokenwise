"""TTL destekli LRU Cache (saf Python, sadece stdlib)."""

import time
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int, ttl: float, now=None):
        self.capacity = capacity
        self.ttl = ttl
        self._now = now if now is not None else time.monotonic
        # key -> (value, yazılma_zamanı); OrderedDict sonu = MRU (en yeni)
        self._data = OrderedDict()

    def _expired(self, timestamp) -> bool:
        return self._now() - timestamp >= self.ttl

    def _purge_expired(self) -> None:
        expired = [k for k, (_, ts) in self._data.items() if self._expired(ts)]
        for k in expired:
            del self._data[k]

    def put(self, key, value) -> None:
        if self.capacity <= 0:
            return
        if key in self._data:
            # Var olan anahtarı güncelle: değeri değiştir, MRU yap, sayı şişmez.
            self._data[key] = (value, self._now())
            self._data.move_to_end(key)
            return
        # Yeni anahtar: yer açmadan önce süresi geçenleri temizle.
        if len(self._data) >= self.capacity:
            self._purge_expired()
        while len(self._data) >= self.capacity:
            # En az yakın zamanda kullanılanı (OrderedDict başı) at.
            self._data.popitem(last=False)
        self._data[key] = (value, self._now())

    def get(self, key):
        if key not in self._data:
            return None
        value, ts = self._data[key]
        if self._expired(ts):
            del self._data[key]
            return None
        # Okumak öğeyi MRU yapar (tahliyeden korur).
        self._data.move_to_end(key)
        return value

    def __len__(self) -> int:
        self._purge_expired()
        return len(self._data)
