from adapters.base import BaseChatAdapter, ChatPlatform
from pathlib import Path
import os
import platform


class MinecraftAdapter(BaseChatAdapter):
    chat_platform = ChatPlatform.MINECRAFT
    chat_identifier_string = "[CHAT]"
    
    def __init__(self):
        super().__init__()
        self.log_file_path = self.get_latest_log()
    
    def normalize(self, raw: dict) -> dict:
        with open(self.log_file_path) as latest_log_file:
            for line in latest_log_file:
                if self.chat_identifier_string in line:
                    print(line)
    
    def get_latest_log(self):
        system = platform.system()

        if system == "Windows": # Windows
            base = Path(os.environ["APPDATA"]) / ".minecraft"
        elif system == "Darwin": # MacOS
            base = Path.home() / "Library/Application Support/minecraft"
        else: # Linux
            base = Path.home() / ".minecraft"

        return base / "logs" / "latest.log"
    
    
