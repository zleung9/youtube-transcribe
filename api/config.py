from pydantic import BaseSettings
from typing import List, Dict
from datetime import time

class EmailConfig(BaseSettings):
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    recipients: List[str]

class ChannelConfig(BaseSettings):
    channel_id: str
    platform: str
    scan_time: time
    enabled: bool = True

class AppConfig(BaseSettings):
    youtube_api_key: str
    email: EmailConfig
    channels: List[ChannelConfig]
    
    class Config:
        env_file = ".env"

    def get_channels(self) -> List[ChannelConfig]:
        return self.channels
    
    def add_channel(self, channel: ChannelConfig):
        self.channels.append(channel)
        self._save()
    
    def remove_channel(self, channel_id: str):
        self.channels = [c for c in self.channels if c.channel_id != channel_id]
        self._save()
    
    def _save(self):
        # Save configuration changes to file/database
        pass
