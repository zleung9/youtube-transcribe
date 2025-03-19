import os
import json
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from yourtube.database import SqliteDB, Video
from yourtube.utils import get_download_dir, download_youtube_video, load_cookies

db = SqliteDB()

class WatchLaterDaemon:
    def __init__(self, db: SqliteDB, cookie_path: str=None):
        self.db = db
        if cookie_path:
            self.cookie_path = cookie_path
        else:
            self.cookie_path = os.path.join(get_download_dir(), 'youtube_cookies.txt')
        
        # Set up logging
        logging.basicConfig(
            filename='watchlater_daemon.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Configure selenium webdriver (Chrome in this example)
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in headless mode
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        # Load cookies from Netscape format file
        self.driver.get('https://www.youtube.com')
        load_cookies(self.driver, self.cookie_path)

    def get_playlist_videos(self):
        """Simulate browser to get video IDs from watch later playlist"""
        try:
            # Replace with your actual watch later playlist URL
            self.driver.get('https://www.youtube.com/playlist?list=WL')
            
            # Wait for videos to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.ID, "video-title"))
            )
            
            # Get all video elements
            video_elements = self.driver.find_elements(By.ID, "video-title")
            videos = []
            
            for element in video_elements:
                video_url = element.get_attribute('href')
                if video_url:
                    video_id = video_url.split('v=')[1]
                    title = element.get_attribute('title')
                    channel = element.find_element(By.XPATH, "../../..").find_element(By.CLASS_NAME, "ytd-channel-name").text
                    videos.append({
                        'video_id': video_id,
                        'title': title,
                        'channel': channel,
                        'process_date': datetime.now()
                    })
            
            return videos
            
        except Exception as e:
            logging.error(f"Error getting playlist videos: {str(e)}")
            return []

    def is_video_downloaded(self, video_id):
        """Check if video is already in database"""
        return self.db.get_video(video_id=video_id) is not None

    def download_video(self, video_data):
        """Download video using download_youtube_video utility"""
        try:
            info = download_youtube_video(
                video_id=video_data['video_id'],
                format="worst",  # Using worst quality as per your previous configuration
                video=True,      # Download the actual video
                json=True,       # Get video metadata
                subtitles=True,  # Download subtitles if available
                auto_subtitles=True,  # Download auto-generated subtitles if manual ones aren't available
                langs=["en", "zh"]  # Download English and Chinese subtitles
            )
            
            if info:
                # Update video data with additional information
                video_data.update({
                    'channel_id': info.get('channel_id'),
                    'upload_date': datetime.strptime(info.get('upload_date'), '%Y%m%d') if info.get('upload_date') else None,
                    'language': info.get('language')
                })
                
                # Create and add video to database
                video = Video.from_dict(video_data)
                self.db.add_video(video)
                
                logging.info(f"Successfully downloaded video: {video_data['title']}")
            else:
                logging.error(f"Failed to download video {video_data['video_id']}: No info returned")
            
        except Exception as e:
            logging.error(f"Error downloading video {video_data['video_id']}: {str(e)}")

    def run(self):
        """Main daemon loop"""
        logging.info("Starting Watch Later Daemon")
        
        while True:
            try:
                # Get current videos in playlist
                videos = self.get_playlist_videos()
                
                # Check for new videos and download them
                for video_data in videos:
                    if not self.is_video_downloaded(video_data['video_id']):
                        logging.info(f"New video found: {video_data['title']}")
                        self.download_video(video_data)
                
                # Wait for 1 minute before next check
                time.sleep(60)
                
            except Exception as e:
                logging.error(f"Error in main loop: {str(e)}")
                time.sleep(60)  # Wait before retrying
            
            finally:
                # Ensure the driver is properly closed if we exit the loop
                try:
                    self.driver.quit()
                except:
                    pass

if __name__ == "__main__":
    daemon = WatchLaterDaemon(db, cookie_path="/Users/zhuliang/Downloads/youtube_cookies.txt")
    daemon.run()
