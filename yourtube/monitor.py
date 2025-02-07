from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime, timezone
from yourtube import SqliteDB, Video, YoutubeVideo
from yt_dlp import YoutubeDL
import re


class Monitor(ABC):
    """Base class for platform-specific monitors"""
    def __init__(self, config: Dict):
        self.config = config
        self.db = SqliteDB()  # Use existing database connection
        
    @abstractmethod
    def get_channel_info(self, channel_id: str) -> Dict:
        """Get channel metadata"""
        pass
    
    @abstractmethod
    def get_latest_videos(self, channel_id: str, max_results: int = 10, until_date: Optional[datetime] = None) -> List[Video]:
        """Get latest videos from channel"""
        pass
    
    
    def process_new_videos(self, channel_id: str) -> List[Video]:
        """Get and process new videos, comparing with database"""
        latest_videos = self.get_latest_videos(channel_id)
        new_videos = []
        
        for video in latest_videos:
            if not self.db.video_exists(video.video_id):
                new_videos.append(video)
                
        return new_videos


class YoutubeMonitor(Monitor):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False
        }
    
    def get_channel_info(self, channel_id: str) -> Dict:
        with YoutubeDL(self.ydl_opts) as ydl:
            try:
                channel_url = f"https://www.youtube.com/channel/{channel_id}"
                info = ydl.extract_info(channel_url, download=False)
                return {
                    'snippet': {
                        'title': info.get('channel'),
                        'description': info.get('description')
                    },
                    'statistics': {
                        'subscriberCount': info.get('subscriber_count'),
                        'videoCount': info.get('video_count')
                    }
                }
            except Exception as e:
                print(f"Error getting channel info: {e}")
                return None
    
    def get_channel_id_from_handle(self, handle: str) -> Optional[str]:
        """Convert a YouTube handle/username to a channel ID"""
        handle = handle.lstrip('@')
        with YoutubeDL(self.ydl_opts) as ydl:
            try:
                # Try with @handle first
                url = f"https://www.youtube.com/@{handle}"
                info = ydl.extract_info(url, download=False)
                # Extract channel ID from channel_url
                channel_url = info.get('channel_url', '')
                channel_id = re.search(r'channel/(UC[\w-]+)', channel_url)
                if channel_id:
                    return channel_id.group(1)
            except:
                return None
        return None

    def get_latest_videos(self, channel_identifier: str, max_results: int = 10, until_date: Optional[datetime] = None) -> List[Video]:
        """Get latest videos from a channel using yt-dlp"""
        # Handle channel identifier
        if channel_identifier.startswith('@') or not channel_identifier.startswith('UC'):
            channel_id = self.get_channel_id_from_handle(channel_identifier)
            if not channel_id:
                raise ValueError(f"Could not find channel ID for handle: {channel_identifier}")
        else:
            channel_id = channel_identifier

        # Set up yt-dlp options for playlist extraction
        playlist_opts = {
            **self.ydl_opts,
            'playlistend': max_results
        }

        videos = []
        with YoutubeDL(playlist_opts) as ydl:
            try:
                # Get channel uploads playlist
                channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
                info = ydl.extract_info(channel_url, download=False)
                
                if not info.get('entries'):
                    return videos

                for entry in info['entries']:
                    # Convert timestamp to datetime
                    upload_date = datetime.strptime(
                        str(entry.get('timestamp')), 
                        '%Y%m%d'
                    ).replace(tzinfo=timezone.utc)
                    
                    # Skip if video is newer than until_date
                    if until_date and upload_date > until_date:
                        continue
                    
                    video = YoutubeVideo(
                        video_id=entry['id'],
                        title=entry['title'],
                        channel_id=channel_id,
                        channel=entry.get('channel', ''),
                        upload_date=upload_date
                    )
                    videos.append(video)
                    
                    if len(videos) >= max_results:
                        break
                        
                return videos
            except Exception as e:
                print(f"Error getting videos: {e}")
                return []


class BilibiliMonitor(Monitor):
    def __init__(self, config: Dict):
        super().__init__(config)
        
    def get_channel_info(self, channel_id: str) -> Dict:
        pass
    
    def get_latest_videos(self, channel_id: str, max_results: int = 10, until_date: Optional[datetime] = None) -> List[Video]:
        pass
        