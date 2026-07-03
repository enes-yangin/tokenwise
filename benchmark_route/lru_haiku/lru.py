"""LRU Cache with TTL support."""

import time
from collections import OrderedDict
from typing import Any, Callable, Optional


class LRUCache:
    """LRU Cache with time-to-live (TTL) support using only stdlib."""

    def __init__(self, capacity: int, ttl: float, now: Optional[Callable[[], float]] = None):
        """
        Initialize LRU cache.

        Args:
            capacity: Maximum number of items to store.
            ttl: Time-to-live in seconds for each item.
            now: Callable that returns current time as float (seconds).
                 If None, uses time.monotonic.
        """
        self.capacity = capacity
        self.ttl = ttl
        self.now = now if now is not None else time.monotonic
        # OrderedDict maintains insertion order; we track access order manually
        self.cache: OrderedDict[Any, tuple[Any, float]] = OrderedDict()

    def _is_expired(self, write_time: float) -> bool:
        """Check if an item has expired based on its write time."""
        return self.now() - write_time >= self.ttl

    def _cleanup_expired(self) -> None:
        """Remove all expired items from cache."""
        current_time = self.now()
        expired_keys = [
            key for key, (_, write_time) in self.cache.items()
            if current_time - write_time >= self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]

    def put(self, key: Any, value: Any) -> None:
        """
        Put a key-value pair in the cache.

        If key already exists, updates its value and marks it as most-recently-used.
        If capacity is exceeded, removes the least-recently-used item.
        """
        if self.capacity <= 0:
            return

        # Clean up expired items first
        self._cleanup_expired()

        # If key already exists, remove it to re-insert at end (MRU)
        if key in self.cache:
            del self.cache[key]

        # Add new entry with current timestamp
        self.cache[key] = (value, self.now())

        # If over capacity, remove least-recently-used (oldest)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    def get(self, key: Any) -> Optional[Any]:
        """
        Get a value from the cache.

        Returns the value if key exists and is not expired, otherwise None.
        Accessing an item marks it as most-recently-used.
        """
        if key not in self.cache:
            return None

        value, write_time = self.cache[key]

        # Check if expired
        if self._is_expired(write_time):
            del self.cache[key]
            return None

        # Move to end to mark as most-recently-used
        self.cache.move_to_end(key)

        return value

    def __len__(self) -> int:
        """Return the number of non-expired items in the cache."""
        self._cleanup_expired()
        return len(self.cache)
