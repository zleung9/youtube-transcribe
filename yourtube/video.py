import os, json
from datetime import datetime
from uuid import uuid4
import yt_dlp
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column, 
    String, 
    DateTime, 
    Boolean, 
    UUID
)
from yourtube.utils import convert_vtt_to_srt, get_download_dir
Base = declarative_base()


class Video(Base):
    """Abstract base class for Video objects"""
    __tablename__ = "videos"

    id              = Column(UUID(as_uuid=True), primary_key=True, unique=True, default=uuid4)
    video_id        = Column(String(20), nullable=False)
    title           = Column(String(200), nullable=False)
    channel_id      = Column(String(20), nullable=True)
    channel         = Column(String(100), nullable=True)
    upload_date     = Column(DateTime)
    process_date    = Column(DateTime)
    language        = Column(String(10), nullable=True)  # Store primary language
    transcript      = Column(Boolean, default=False)
    fulltext        = Column(Boolean, default=False)
    summary         = Column(Boolean, default=False)
    _metadata       = {} # metadata from the 
    _default_path   = get_download_dir()

    def __repr__(self):
        return f"<Video(video_id='{self.video_id}', title='{self.title}', channel='{self.channel}')>"
    
    @property
    def short_id(self):
        return self.id[:6]

    @classmethod
    def from_dict(cls, data):
        '''Create video object from JSON data
        Args:
            data: the dicionary containing info of the video
        Returns:
            Video: video instance
        '''
        return cls(**data)


    def to_dict(self):
        '''Convert video object to dictionary for selection
        Returns:
            dict: dictionary of video object
        '''
        return {
            'id': self.id,
            "video_id": self.video_id,
            'title': self.title,
            'channel': self.channel,
            'channel_id': self.channel_id,
            'upload_date': self.upload_date,
            'process_date': self.process_date,
            'language': self.language,
            'transcript': self.transcript,
            'fulltext': self.fulltext,
            'summary': self.summary
        }
    
    def update(self, **kwargs):
        '''Update the video object with new attributes'''
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def get(self, *args, **kwargs):
        '''Download the video. 
        Output: video_id.*.json, video_id.srt, video_id.mp4
        '''
        raise NotImplementedError



class YoutubeVideo(Video):
    def __init__(self):
        super().__init__()

    def get(self, video_id, download_video=False, download_json=False, format='worst'):
        '''
        Download a YouTube video using yt-dlp library.
        Parameters:
        - video_id: str, YouTube video ID
        - download: bool, whether to download the video
        - path: str, path to save the video
        - quality: str, quality of the video to download
        Returns:
        - metadata: dict, metadata of the video
        '''
        
        # load info either from local json or downlaod
        json_path = os.path.join(self._default_path, f"{video_id}.info.json")
        if not download_json:
            info = json.load(json_path)
        else:
            ydl_opts = {
                'quiet': False,
                'extract_flat': True,
                'outtmpl': os.path.join(self._default_path, f'{video_id}.%(ext)s'),
                'format': format,
                'writeinfojson': True,
                'writesubtitles': True,
                'writeautomaticsub': True,  # Enable auto-generated subtitles if manual ones aren't available'
                'subtitleslangs': ['en', "zh"]
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(
                    url=f"https://www.youtube.com/watch?v={video_id}", 
                    download=download_video
                )
        
        video_title = info.get('title', 'Untitled')
        video_ext = info['ext']
        
        # get the real language
        try:
            _ = open(json_path.replace('.info.json', '.zh.srt'), 'r')
            language = 'zh'
        except FileNotFoundError:
            try:
                _ = open(json_path.replace('.info.json', '.en.srt'), 'r')
                language = 'en'
            except FileNotFoundError:
                language = None
        
        # Set the actual video path with the correct extension
        vtt_path = os.path.join(self._default_path, f'{video_id}.vtt')
        if not os.path.exists(vtt_path):
            vtt_path = None
            srt_path = None
        else:
            try:
                srt_path = convert_vtt_to_srt(vtt_path)
                print(f"vtt converted to srt: {srt_path}")
            except FileNotFoundError:
                srt_path = None
                # even vtt is not available, we still need to keep path, usually this is the case for "zh"
                print("No subtitles for this video, transcribe it please")
        
        video_path = os.path.join(self._default_path, f'{video_id}.{video_ext}')
        if not os.path.exists(video_path):
            video_path = None

        # rename paths    
        self._metadata = {
            "video_id": video_id,
            'title': video_title,
            'video_ext': video_ext,
            'channel': info.get('channel', ""),
            'channel_id': info.get('channel_id', ""),  # Added channel_id extraction
            'language': language,
            'upload_date': info.get('upload_date'),
            'has_video': 1 if video_path else 0,
            'has_vtt': 1 if vtt_path else 0,
            'has_srt': 1 if srt_path else 0
        }

        # Update key value 
        for key, value in self._metadata.items():
            if hasattr(self, key):
                setattr(self, key, value)
        # Convert upload_date string to datetime object
        if isinstance(self.upload_date, str):
            self.upload_date = datetime.strptime(self.upload_date, '%Y%m%d')
