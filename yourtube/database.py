import os
import glob
from uuid import uuid4
from abc import ABC, abstractmethod
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import (
    Column, 
    String, 
    DateTime, 
    Boolean, 
    UUID
)
from yourtube.utils import get_download_dir, get_db_path

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
            'id': str(self.id),
            "video_id": self.video_id,
            'title': self.title,
            'channel': self.channel,
            'channel_id': self.channel_id,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'process_date': self.process_date.isoformat() if self.process_date else None,
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


class Database(ABC):
    def __init__(self, db_path=None):
        if db_path is None:
            self.db_path = get_db_path()
        else:
            self.db_path = db_path

    def add_video(self, video):
        return self._add_video(video)

    def delete_video(self, **kwargs):
        return self._delete_video(**kwargs)
    
    def refresh_database(self):
        raise NotImplementedError
    
    def get_video(self, **kwargs):
        return  self._get_video(**kwargs)

    
    def update_video(self, video: Video):
        """Update an existing video in the database without deleting/re-adding."""
        try:
            # Get existing video
            existing_video = self.get_video(video_id=video.video_id)
            
            if existing_video:
                # Get attributes from the new video object, excluding 'id'
                update_data = video.to_dict()
                update_data.pop('id', None)  # Remove the id field
                
                # Use the Video's update method with filtered attributes
                existing_video.update(**update_data)
                
                # Commit the changes
                self.session.commit()
                return True
            else:
                # If video doesn't exist, add it
                return self.add_video(video)
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Error updating video: {str(e)}")
    
    @abstractmethod
    def _add_video(self, video: Video):
        """Add a new video to the database."""
        raise NotImplementedError
    
    @abstractmethod
    def _delete_video(self, **kwargs):
        """Delete a video from the database."""
        raise NotImplementedError
    
    @abstractmethod
    def _get_video(self, **kwargs):
        """Get a video from the database."""
        raise NotImplementedError


class SqliteDB(Database):
    def __init__(self, db_path='videos.db'):
        super().__init__(db_path)
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        Base.metadata.create_all(self.engine)  # Create tables if they don't exist
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def _add_video(self, video: Video):
        """Add a new video to the database."""
        try:
            self.session.add(video)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Error adding video: {str(e)}")

    def _delete_video(self, **kwargs):
        """Delete a video from the database."""
        try:
            video = self.get_video(**kwargs)
            if video:
                self.session.delete(video) # remove from database
                self.session.commit() 
                for file in glob.glob(f"{get_download_dir()}/{video.video_id}.*", recursive=True):
                    print(file)
                    try:
                        os.remove(file)
                    except OSError as e:
                        print(f"Error deleting file: {file}")
                print(f"Successfully deleted videos filtered by: {kwargs}")
                return True
            else:
                print(f"No videos found filtered by: {kwargs}")
                return False
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Error deleting video: {str(e)}")

    def _get_video(self, **kwargs):
        '''If video_id exists in database, return video, other wise None
        '''
        try:
            video = self.session.query(Video).filter_by(**kwargs).first()
            return video
        except Exception as e:
            self.session.rollback()
            raise IndexError(f"Something went wrong when trying to get video: {e}")
            return None

if __name__ == "__main__":
    db = SqliteDB()
    deleted = db.delete_video(video_id="HeHnTfkCcok")
    print(f"Deleted: {deleted}")
