import os
from googleapiclient.discovery import build
import yt_dlp
from youtube.utils import load_config
import argparse

def get_latest_video_id():

    config = load_config()
    youtube_config = config['youtube']

    youtube = build('youtube', 'v3', developerKey=youtube_config['api_key'])
    request = youtube.channels().list(
        part='contentDetails',
        id=youtube_config['channel_id']
    )
    response = request.execute()
    uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    request = youtube.playlistItems().list(
        part='snippet',
        playlistId=uploads_playlist_id,
        maxResults=1
    )
    response = request.execute()
    latest_video_id = response['items'][0]['snippet']['resourceId']['videoId']
    return latest_video_id

def download_video(video_id):
    config = load_config()
    download_path = config['paths']['downloads']

    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        'format': 'best',
        'writeinfojson': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_title = info['title']
        video_ext = info['ext']
        return os.path.join(download_path, f"{video_title}.{video_ext}")

def main():
    parser = argparse.ArgumentParser(description="YouTube Video Downloader")
    parser.add_argument("-y", '--video_id', type=str, help="YouTube video ID to download")
    args = parser.parse_args()

    video_path = download_video(args.video_id)
    print(f"Video downloaded: {video_path}")

if __name__ == "__main__":
    main()
