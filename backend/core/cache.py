from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Generic, TypeVar, cast
from collections import defaultdict
from sqlalchemy.orm import Session
from backend.core.config import MESSAGE_CACHE_TTL
from adapters.platforms import ChatPlatform
from backend.services.messages import get_server_messages


K = TypeVar("K")
V = TypeVar("V")


@dataclass(slots=True)
class CacheEntry(Generic[V]):
    value: V
    expires_at: float


class SlidingCache(Generic[K, V]):
    def __init__(self, ttl: float):
        self._ttl = ttl
        self._cache: dict[K, CacheEntry[V]] = {}
        self._lock = Lock()

    def get(self, key: K) -> V | None:
        now = monotonic()

        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            # Upon expiry remove it
            if entry.expires_at <= now:
                del self._cache[key]
                return None

            # Reset the ttl upon access
            entry.expires_at = now + self._ttl
            return entry.value

    def set(self, key: K, value: V) -> None:
        with self._lock:
            self._cache[key] = CacheEntry(
                value=value, expires_at=monotonic() + self._ttl
            )

    def add(self, key: K, value: V) -> None:
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                entry = CacheEntry(
                    # Cast to satisfy type check
                    value=cast(V, []),
                    expires_at=monotonic() + self._ttl,
                )
                self._cache[key] = entry

            if not isinstance(entry.value, list):
                raise TypeError(
                    f"Expected list at key {key!r}, got {type(entry.value).__name__}"
                )

            entry.value.append(value)

    def remove(self, key: K) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def cleanup(self) -> None:
        now = monotonic()

        with self._lock:
            expired_keys = [
                k for k, entry in self._cache.items() if entry.expires_at <= now
            ]
            for k in expired_keys:
                del self._cache[k]


message_cache = SlidingCache(ttl=MESSAGE_CACHE_TTL)


def sync_message_cache(db: Session, platform: ChatPlatform, server_id: str):
    cache = message_cache.get(server_id)
    if cache is None:
        messages = get_server_messages(db, platform, server_id)
        message_cache.set(server_id, {"collection": [], "map": defaultdict(list)})
        cache = message_cache.get(server_id)
        if cache is not None:
            cache["collection"] = messages
            for m in messages:
                cache["map"][m.user_id].append(m)
