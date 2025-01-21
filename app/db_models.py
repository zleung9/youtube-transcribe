from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class Video(Base):
    __tablename__ = 'videos'
    
    id = Column(Integer, primary_key=True)
    video_id = Column(String(20), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    processed_date = Column(DateTime, default=datetime.datetime.utcnow)
    video_path = Column(String(500))
    transcript_path = Column(String(500))
    summary_path = Column(String(500))
    summary_text = Column(Text)
    duration = Column(Integer)  # in seconds
    language = Column(String(10))
    
    def __repr__(self):
        return f"<Video(title='{self.title}', video_id='{self.video_id}')>"

# Create database and tables
engine = create_engine('sqlite:///videos.db', echo=True)
Base.metadata.create_all(engine)

# Create session factory
Session = sessionmaker(bind=engine)