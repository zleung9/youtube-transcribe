from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
from yourtube import SqliteDB, Video, YoutubeVideo
from googleapiclient.discovery import build


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
        self.youtube = build('youtube', 'v3', 
                           developerKey=config['youtube']['api_key'])
    
    def get_channel_info(self, channel_id: str) -> Dict:
        request = self.youtube.channels().list(
            part="snippet,contentDetails,statistics",
            id=channel_id
        )
        response = request.execute()
        return response['items'][0] if response['items'] else None
    
    def get_channel_id_from_handle(self, handle: str) -> Optional[str]:
        """Convert a YouTube handle/username to a channel ID"""
        # Remove @ if present
        handle = handle.lstrip('@')
        
        # Try searching for the channel
        request = self.youtube.search().list(
            part="snippet",
            q=handle,
            type="channel",
            maxResults=1
        )
        response = request.execute()
        
        # Return the channel ID if found
        if response.get('items'):
            return response['items'][0]['id']['channelId']
        return None

    def get_latest_videos(self, channel_identifier: str, max_results: int = 10, until_date: Optional[datetime] = None) -> List[Video]:
        """
        Get latest videos from a channel using either channel ID or handle/username
        Args:
            channel_identifier: Channel ID or handle (with or without @)
            max_results: Maximum number of videos to return
            until_date: Optional date to get videos until
        """
        # If the identifier starts with @ or doesn't look like a channel ID, treat it as a handle
        if channel_identifier.startswith('@') or not channel_identifier.startswith('UC'):
            channel_id = self.get_channel_id_from_handle(channel_identifier)
            if not channel_id:
                raise ValueError(f"Could not find channel ID for handle: {channel_identifier}")
        else:
            channel_id = channel_identifier

        request = self.youtube.search().list(
            part="snippet",
            channelId=channel_id,
            order="date",
            maxResults=max_results
        )
        response = request.execute()
        
        videos = []
        for item in response['items']:
            if item['id']['kind'] == 'youtube#video':
                upload_date = datetime.strptime(
                    item['snippet']['publishedAt'], 
                    '%Y-%m-%dT%H:%M:%SZ'
                )
                
                # If until_date is specified and the video is newer, skip it
                if until_date and upload_date > until_date:
                    continue
                    
                video = YoutubeVideo(
                    video_id=item['id']['videoId'],
                    title=item['snippet']['title'],
                    channel_id=channel_id,
                    channel=item['snippet']['channelTitle'],
                    upload_date=upload_date
                )
                videos.append(video)
                
                # If we have enough videos up to the specified date, stop processing
                if until_date and len(videos) >= max_results:
                    break
        
        return videos


class BilibiliMonitor(Monitor):
    def __init__(self, config: Dict):
        super().__init__(config)
        
    def get_channel_info(self, channel_id: str) -> Dict:
        pass
    
    def get_latest_videos(self, channel_id: str, max_results: int = 10, until_date: Optional[datetime] = None) -> List[Video]:
        pass
        