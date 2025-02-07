import os, glob
from abc import ABC, abstractmethod
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from yourtube import Video
from yourtube.utils import get_download_dir
Base = declarative_base()


class Database(ABC):
    def __init__(self):
        pass

    def add_video(self, video):
        return self._add_video(video)

    def delete_video(self, **kwargs):
        return self._delete_video(**kwargs)
    
    def refresh_database(self):
        raise NotImplementedError
    
    def get_video(self, **kwargs):
        return  self._get_video(**kwargs)

    
    def update_video(self, video: Video):
        """Refresh database with new video information."""
        existing_video = self.get_video(video)
        if existing_video:
            self.delete_video(existing_video)
        self.add_video(video)
        return True
    
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
        super().__init__()
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
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
