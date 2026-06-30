from adapters.base import BaseChatAdapter, ChatPlatform


class RobloxAdapter(BaseChatAdapter):
    platform = ChatPlatform.ROBLOX

    def normalize(self, raw: dict) -> dict:
        assert isinstance(raw, dict), "Roblox chat_group must be a dict"
        return raw
