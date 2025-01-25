from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date
import os

Base = declarative_base()

class Video(Base):
    __tablename__ = 'videos'
    id = Column(Integer, primary_key=True)
    video_id = Column(String(20), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    channel_id = Column(String(20))
    channel = Column(String(100))
    upload_date = Column(DateTime)
    process_date = Column(DateTime)
    language = Column(String(10))  # Store primary language
    transcript = Column(Boolean, default=False)
    summary = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Video(video_id='{self.video_id}', title='{self.title}', channel='{self.channel}')>"
    
    @classmethod
    def from_info(cls, info):
        video = cls()
        video.update_info(info)
        return video

    def update_info(self, info):
        self.video_id = info['video_id']
        self.title = info['title']
        self.channel = info['channel']
        self.channel_id = info['channel_id']  # Update channel_id
        self.language = info['language']
        self.upload_date = datetime.strptime(info['upload_date'], '%Y%m%d').date()
        self.process_date = date.today()


def init_db(db_path='videos.db'):
    # Only create tables if the database doesn't exist
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    
    # Check if tables already exist
    if not os.path.exists(db_path):
        Base.metadata.create_all(engine)
    
    return engine

# Create database and tables
engine = init_db()

# Create session factory
Session = sessionmaker(bind=engine)