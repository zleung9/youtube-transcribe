import os
from googleapiclient.discovery import build
import yt_dlp  # Changed from youtube_dl to yt_dlp
from config import YOUTUBE_API_KEY, CHANNEL_ID, DOWNLOAD_PATH

def get_latest_video_id():
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    request = youtube.channels().list(
        part='contentDetails',
        id=CHANNEL_ID
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
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
