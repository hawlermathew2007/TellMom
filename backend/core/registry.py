from enum import Enum


# TODO: would this cause more synchronization to be performed
class ChatPlatform(Enum):
    ROBLOX = "roblox"
    DISCORD = "discord"
    MINECRAFT = "minecraft"
