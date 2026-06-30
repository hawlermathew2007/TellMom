from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from core import config
from schemas.grooming import GroomingAnalysis


@dataclass
class CachedMessage:
    platform: str
    server_id: str
    user_id: str
    message: str
    created_at: datetime


class MessageCache:
    def __init__(self, ttl_hours: int | None = None) -> None:
        self._ttl = timedelta(hours=ttl_hours or config.MESSAGE_CACHE_TTL_HOURS)
        self._entries: list[CachedMessage] = []

    def _purge_expired(self) -> None:
        cutoff = datetime.now(UTC) - self._ttl
        self._entries = [entry for entry in self._entries if entry.created_at >= cutoff]

    def add(self, platform: str, server_id: str, user_id: str, message: str) -> None:
        self._purge_expired()
        self._entries.append(
            CachedMessage(
                platform=platform,
                server_id=server_id,
                user_id=user_id,
                message=message,
                created_at=datetime.now(UTC),
            )
        )


message_cache = MessageCache()


class ExplanationCache:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], GroomingAnalysis] = {}

    def get(self, key: tuple[str, str]) -> GroomingAnalysis | None:
        return self._entries.get(key)

    def set(self, key: tuple[str, str], analysis: GroomingAnalysis) -> None:
        self._entries[key] = analysis


explanation_cache = ExplanationCache()
