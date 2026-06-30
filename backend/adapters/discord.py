from adapters.base import BaseChatAdapter, ChatPlatform


class DiscordAdapter(BaseChatAdapter):
    platform = ChatPlatform.DISCORD

    def normalize(self, raw: dict) -> dict:
        raise NotImplementedError(f"{self.platform.value} adapter is not yet implemented")
