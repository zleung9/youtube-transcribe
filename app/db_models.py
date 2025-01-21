from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
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
    channel_name = Column(String(100))  # Changed from 'channel' to 'channel_name'
    processed_date = Column(DateTime, default=datetime.datetime.utcnow)
    video_path = Column(String(500))
    transcript_path = Column(String(500))
    summary_path = Column(String(500))
    summary_text = Column(Text)
    
    def __repr__(self):
        return f"<Video(title='{self.title}', video_id='{self.video_id}')>"

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