from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from adapters.base import ChatPlatform
from core import config
from schemas.grooming import GroomingAnalysis


@dataclass
class CachedMessage:
    platform: ChatPlatform
    server_id: str
    user_id: str
    message: str
    created_at: datetime


class MessageCache:
    """
    Store message with context metadata and expire them accordingly using custom
    implementation since simple ttl list expire whole key content.
    """

    def __init__(self, ttl_hours: int | None = None) -> None:
        self._ttl = timedelta(hours=ttl_hours or config.MESSAGE_CACHE_TTL_HOURS)
        self._entries: list[CachedMessage] = []

    def _purge_expired(self) -> None:
        cutoff = datetime.now(UTC) - self._ttl
        self._entries = [entry for entry in self._entries if entry.created_at >= cutoff]

    def add(
        self, platform: ChatPlatform, server_id: str, user_id: str, message: str
    ) -> None:
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

    def get_server_entries(
        self, platform: ChatPlatform, server_id: str
    ) -> list[CachedMessage]:
        """Get all latest chat messages of server group."""
        self._purge_expired()
        return [
            entry
            for entry in self._entries
            if entry.platform == platform and entry.server_id == server_id
        ]

    def count_server_messages(self, platform: ChatPlatform, server_id: str) -> int:
        return len(self.get_server_entries(platform, server_id))


class ExplanationCache:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], GroomingAnalysis] = {}

    def get(self, key: tuple[str, str]) -> GroomingAnalysis | None:
        return self._entries.get(key)

    def set(self, key: tuple[str, str], analysis: GroomingAnalysis) -> None:
        self._entries[key] = analysis


message_cache = MessageCache()
explanation_cache = ExplanationCache()
