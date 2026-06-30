from schemas.grooming import GroomingAnalysis


class MessageCache:
    def __init__(self):
        self.counts: dict[str, int] = {}
        self.messages: dict[str, list[str]] = {}

    def update(self, chat_group: dict[str, list[str]]) -> dict[str, list[str]]:
        new_messages: dict[str, list[str]] = {}

        for user_id, msgs in chat_group.items():
            if user_id not in self.messages:
                self.messages[user_id] = []
            self.messages[user_id].extend(msgs)

            new_count = len(self.messages[user_id])
            if new_count > self.counts.get(user_id, 0):
                self.counts[user_id] = new_count
                new_messages[user_id] = msgs

        return new_messages

    def get_messages(self, user_id: str) -> list[str]:
        return self.messages.get(user_id, [])

    def all_counts(self) -> dict[str, int]:
        return dict(self.counts)


message_cache = MessageCache()


class ExplanationCache:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], GroomingAnalysis] = {}

    def get(self, key: tuple[str, str]) -> GroomingAnalysis | None:
        return self._entries.get(key)

    def set(self, key: tuple[str, str], analysis: GroomingAnalysis) -> None:
        self._entries[key] = analysis


explanation_cache = ExplanationCache()
