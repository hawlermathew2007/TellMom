from adapters.base import BaseChatAdapter, ChatPlatform


class MinecraftAdapter(BaseChatAdapter):
    platform = ChatPlatform.MINECRAFT

    def normalize(self, raw: dict) -> dict:
        raise NotImplementedError(f"{self.platform.value} adapter is not yet implemented")
