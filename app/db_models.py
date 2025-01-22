from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os

Base = declarative_base()

class Video(Base):
    __tablename__ = 'videos'
    id = Column(Integer, primary_key=True)
    video_id = Column(String(20), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    channel_id = Column(String(20))
    channel = Column(String(100))
    date = Column(DateTime)
    language = Column(String(10))  # Store primary language
    transcript = Column(Boolean, default=False)
    summary = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Video(video_id='{self.video_id}', title='{self.title}', channel='{self.channel}')>"


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