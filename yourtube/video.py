from uuid import uuid4
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column, 
    String, 
    DateTime, 
    Boolean, 
    UUID
)
from yourtube.utils import get_download_dir
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


    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

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