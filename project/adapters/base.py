from abc import ABC, abstractmethod
from enum import Enum


class ChatPlatform(Enum):
    ROBLOX = "roblox"
    DISCORD = "discord"
    MINECRAFT = "minecraft"


class BaseChatAdapter(ABC):
    platform: ChatPlatform

    @abstractmethod
    def normalize(self, raw: dict) -> dict:
        """Convert platform-specific payload into canonical chat group format."""
