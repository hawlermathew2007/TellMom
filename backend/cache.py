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
