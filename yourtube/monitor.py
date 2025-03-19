from typing import List, Dict, Optional
from datetime import datetime
from yourtube import Video
from yourtube.utils import get_download_dir, convert_vtt_to_srt, download_youtube_video, load_config
import yt_dlp
import os


class Monitor:
    """Base class for platform-specific monitors"""
    def __init__(self, config: Dict):
        self._default_path = get_download_dir()
        self._config = config
    
    def check_updates(self, handle: str, max_results: int = 10, until_date: str="", end_date: str="") -> List[Video]:
        """Get latest videos from a single channel. 

        Args:
            channel_id (str): The channel ID or handle to fetch videos from
            max_results (int, optional): Maximum number of videos to return. Defaults to 5.
            until_date (datetime, optional): Only return videos published before this date. Defaults to None.

        Returns:
            List[video_id]: List of video ids representing the latest videos from the channel
        """
        raise NotImplementedError
    
    def download(self, video_id: str):
        """Download the video from the platform"""
        raise NotImplementedError



class YoutubeMonitor(Monitor):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False
        }
    
    def get_video_info(self, video_id):
        """
        Get basic information about a video without downloading it
        
        Args:
            video_id (str): YouTube video ID
            
        Returns:
            dict: Dictionary containing basic video information
        """
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'no_warnings': True,
            'writeinfojson': False,
            'noplaylist': True
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                # Extract only the needed information
                return {
                    'title': info.get('title', f'Video {video_id}'),
                    'channel': info.get('uploader', 'Unknown channel'),
                    'upload_date': info.get('upload_date', '')
                }
        except Exception as e:
            print(f"Error getting video info: {str(e)}")
            return {
                'title': f'Processing: {video_id}',
                'channel': 'Loading...',
                'upload_date': ''
            }

    def check_updates(self, channel_handle, max_results=1):
        """
        Fetches latest videos from a YouTube channel (by handle) from a given date span.

        Parameters:
            - channel_handle: YouTube channel handle (e.g., "@ChannelHandle")
            - until_date: Cutoff date in "YYYYMMDD" format (e.g., "20240101" for Jan 1, 2024)
            - max_results: Maximum number of videos to check (default: 50)

        Returns:
            - List of video ids uploaded until the given date.
        """
        
        url = f"https://www.youtube.com/@{channel_handle}"
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,  # Extract metadata without downloading
            'playlistend': max_results  # Fetch up to `max_results` videos
        }

        video_ids = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        video_entries = info['entries']
        if not video_entries[0].get("url", None): # some channels have two layers of entries
                video_entries = video_entries[0]['entries']

        for video in video_entries:
            video_ids.append(video['id'])

        return video_ids


    def download(self, video_id, format='worst'):
        '''
        Download a YouTube video using yt-dlp library.
        
        Parameters:
            - video_id: str, YouTube video ID
            - format: str, format/quality specification for yt-dlp (default: 'worst')
            
        Returns:
            - Video: Video object containing metadata and file paths
            - None: If download fails
        '''
        
        # load info either from local json or downlaod
        info = download_youtube_video(path=self._default_path, video_id=video_id, video=False)
        video_title = info.get('title', 'Untitled')
        
        # get the language from the config: auto, zh, en, and info
        if 'subtitles' in info and info['subtitles']:
            language = next((lang_code for lang_code in info['subtitles'] if lang_code in ['en', 'zh']), None)
        else:
            language = info.get("language") # if auto, get the language from the video info
            if language is None:
                language = "zh"
        
        # get srt path
        srt_path = os.path.join(self._default_path, f'{video_id}.{language}.srt')
        if not os.path.exists(srt_path):
            srt_path = None
            vtt_path = os.path.join(self._default_path, f'{video_id}.{language}.vtt')
            try:
                srt_path = convert_vtt_to_srt(vtt_path)
                print(f"vtt converted to srt: {srt_path}")
            except FileNotFoundError:
                srt_path = None
                vtt_path = None
                _ = download_youtube_video(path=self._default_path, video_id=video_id, format=format, video=True)
                print("No subtitles for this video, transcribe it please")


        # rename paths    
        video = Video.from_dict({
            "video_id": video_id,
            'title': video_title,
            'channel': info.get('channel', ""),
            'channel_id': info.get('channel_id', ""),  # Added channel_id extraction
            'language': language,
            'upload_date': info.get('upload_date'),
            'transcript': True if srt_path else False
        })

        return video


    def get_watch_later_playlist(self, max_results=10, cookie_path=None):
        """
        Fetches videos from your YouTube 'Watch Later' playlist.
        
        Parameters:
            - max_results: Maximum number of videos to fetch (default: 10)
            
        Returns:
            - List of video IDs from your Watch Later playlist
        """
        # URL for Watch Later playlist
        url = "https://www.youtube.com/playlist?list=WL"
        
        if cookie_path is None:
            cookie_path = os.path.join(self._default_path, 'youtube_cookies.txt')
        
        # Options for yt-dlp with authentication
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,  # Extract metadata without downloading
            'playlistend': max_results,  # Fetch up to max_results videos
            'cookiefile': cookie_path,  # Path to your cookies file
            # Alternatively, you can use username and password:
            # 'username': 'your_youtube_username',
            # 'password': 'your_youtube_password',
        }
        
        video_ids = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' in info:
                    for video in info['entries']:
                        video_ids.append(video['id'])
        except Exception as e:
            print(f"Error accessing Watch Later playlist: {str(e)}")
        
        return video_ids


class BilibiliMonitor(Monitor):
    def __init__(self, config: Dict):
        super().__init__(config)
        
    def get_channel_info(self, channel_id: str) -> Dict:
        pass
    
    def get_latest_videos(self, channel_id: str, max_results: int = 10, until_date: Optional[datetime] = None) -> List[Video]:
        pass
        

if __name__ == "__main__":
    monitor = YoutubeMonitor(config=load_config())
    video_ids = monitor.get_watch_later_playlist(
        max_results=10, 
        cookie_path="/Users/zhuliang/Downloads/youtube_cookies.txt"
    )
    print(video_ids)
