# main.py

import os
from downloader import get_latest_video_id, download_video

def main():
    if not os.path.exists('./downloads'):
        os.makedirs('./downloads')

    latest_video_id = get_latest_video_id()

    downloaded_videos_file = 'downloaded_videos.txt'
    if os.path.exists(downloaded_videos_file):
        with open(downloaded_videos_file, 'r') as file:
            downloaded_videos = file.read().splitlines()
    else:
        downloaded_videos = []

    if latest_video_id not in downloaded_videos:
        download_video(latest_video_id)
        
        with open(downloaded_videos_file, 'a') as file:
            file.write(f"{latest_video_id}\n")
        
        print(f"New video downloaded: https://www.youtube.com/watch?v={latest_video_id}")
    else:
        print("No new video found.")

if __name__ == "__main__":
    main()