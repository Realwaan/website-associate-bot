"""Simple in-memory TTL cache for hot database lookups.

Avoids repeated round-trips to Supabase for values that change rarely
(user roles, thread metadata).  Each entry expires after `ttl` seconds.
Thread-safe via a plain dict + lock (the bot is single-process).
"""

import time
import threading
from typing import Any

_lock = threading.Lock()
_store: dict[str, tuple[Any, float]] = {}   # key → (value, expiry_timestamp)


def cache_get(key: str) -> tuple[bool, Any]:
    """Return (hit, value).  Expired entries are treated as misses."""
    with _lock:
        entry = _store.get(key)
        if entry is None:
            return False, None
        value, expiry = entry
        if time.monotonic() > expiry:
            del _store[key]
            return False, None
        return True, value


def cache_set(key: str, value: Any, ttl: float) -> None:
    """Store value under key for ttl seconds."""
    with _lock:
        _store[key] = (value, time.monotonic() + ttl)


def cache_delete(key: str) -> None:
    """Explicitly invalidate a cache entry (e.g. after a write)."""
    with _lock:
        _store.pop(key, None)


def cache_delete_prefix(prefix: str) -> None:
    """Invalidate all entries whose key starts with prefix."""
    with _lock:
        keys = [k for k in _store if k.startswith(prefix)]
        for k in keys:
            del _store[k]


# ── TTL constants ──────────────────────────────────────────────────────────────
ROLE_TTL   = 300   # 5 minutes  — roles change rarely
THREAD_TTL =  30   # 30 seconds — status changes more often
