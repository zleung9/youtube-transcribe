# main.py

import os
from youtube.downloader import get_latest_video_id, download_video
from youtube.transcriber import transcribe_video, process_transcription
from youtube.utils import load_config

def main():
    config = load_config()
    downloads_path = config['paths']['downloads']
    if not os.path.exists(downloads_path):
        os.makedirs(downloads_path)

    latest_video_id = get_latest_video_id()

    downloaded_videos_file = 'downloaded_videos.txt'
    if os.path.exists(downloaded_videos_file):
        with open(downloaded_videos_file, 'r') as file:
            downloaded_videos = file.read().splitlines()
    else:
        downloaded_videos = []

    if latest_video_id not in downloaded_videos:
        # Download video and get the file path
        video_path = download_video(latest_video_id)
        print(f"New video downloaded: https://www.youtube.com/watch?v={latest_video_id}")
        
        # Transcribe the video
        print("Starting transcription...")
        srt_path = transcribe_video(video_path)
        print(f"Transcription completed. SRT file saved at: {srt_path}")
        
        # Generate summary
        print("Generating summary...")
        summary = process_transcription(srt_path, task="summarize")
        print("\nVideo Summary:")
        print(summary)

        with open(downloaded_videos_file, 'a') as file:
            file.write(f"{latest_video_id}\n")
        
        print(f"New video downloaded: https://www.youtube.com/watch?v={latest_video_id}")
    else:
        print("No new video found.")

if __name__ == "__main__":
    main()
