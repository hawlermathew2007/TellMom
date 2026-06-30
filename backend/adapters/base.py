from abc import ABC, abstractmethod
from enum import Enum

class ChatPlatform(Enum):
    DISCORD = "discord"
    MINECRAFT = "minecraft"


class BaseChatAdapter(ABC):
    chat_platform: ChatPlatform

    @abstractmethod
    def normalize(self, raw: dict) -> dict:
        """Convert platform-specific payload into canonical chat group format."""
