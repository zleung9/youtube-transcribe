from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime, timezone
from yourtube import SqliteDB, Video, YoutubeVideo
from yt_dlp import YoutubeDL
import re


class Monitor(ABC):
    """Base class for platform-specific monitors"""
    def __init__(self):
        pass
    
    @abstractmethod
    def _get_latest_videos(self, 
        handle: str, # channel handle/user 
        max_results: int = 10, 
        until_date: Optional[datetime] = None # no later than this date
    ) -> List[Video]:
        """Get latest videos from a single channel. 

        Args:
            channel_id (str): The channel ID or handle to fetch videos from
            max_results (int, optional): Maximum number of videos to return. Defaults to 5.
            until_date (datetime, optional): Only return videos published before this date. Defaults to None.

        Returns:
            List[Video]: List of Video objects representing the latest videos from the channel
        """
        pass
    
    
    def _exists_in_database(self, video_id):
        """Whether the video exists in the database"""
        return self.db.get_video(video_id=video_id) is not None


    def pull(self):
        """Pull from the platform the latest videos and add them to the database"""
        videos = self._get_latest_videos()
        for video in videos:
            if not self._exists_in_database(video.video_id):
                self.db.add_video(video)
        
        return videos

class YoutubeMonitor(Monitor):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False
        }
    

    def _get_latest_videos(self, channel_handle, until_date=None, max_results=50):
        """
        Fetches latest videos from a YouTube channel (by handle) until a specified date.

        Parameters:
            - channel_handle: YouTube channel handle (e.g., "@ChannelHandle")
            - until_date: Cutoff date in "YYYYMMDD" format (e.g., "20240101" for Jan 1, 2024)
            - max_results: Maximum number of videos to check (default: 50)

        Returns:
            - List of videos uploaded until the given date.
        """
        if until_date is None:
            until_date = datetime.now().strftime("%Y%m%d")
            max_results = 1 # only get one latest video
        else:
            until_date = datetime.strptime(until_date, "%Y%m%d")
        
        url = f"https://www.youtube.com/{channel_handle}"
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,  # Extract metadata without downloading
            'playlistend': max_results  # Fetch up to `max_results` videos
        }

        filtered_videos = []
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            for video in info['entries']:
                if video.get('upload_date') > until_date:
                    continue

                filtered_videos.append(
                    Video.from_dict({
                        "video_id": video['id'],
                        'title': video['title'],
                        'channel': video['channel'],
                        'channel_id': video['channel_id'],
                        'upload_date': video['upload_date'],
                    })
                )

            return filtered_videos


    

class BilibiliMonitor(Monitor):
    def __init__(self, config: Dict):
        super().__init__(config)
        
    def get_channel_info(self, channel_id: str) -> Dict:
        pass
    
    def get_latest_videos(self, channel_id: str, max_results: int = 10, until_date: Optional[datetime] = None) -> List[Video]:
        pass
        