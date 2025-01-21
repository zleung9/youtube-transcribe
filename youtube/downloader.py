import os
from googleapiclient.discovery import build
import yt_dlp
from youtube.utils import load_config, convert_vtt_to_srt, rename_title
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
        maxResults=1,
        
    )
    response = request.execute()
    latest_video_id = response['items'][0]['snippet']['resourceId']['videoId']
    return latest_video_id


def download_video(video_id):
    config = load_config()
    download_path = config['paths']['downloads']
    ydl_opts = {
        'outtmpl': os.path.join(download_path, '%(id)s.%(ext)s'),
        'format': 'worst',
        'writeinfojson': False,
        'writesubtitles': True,
        'writeautomaticsub': True,  # Enable auto-generated subtitles if manual ones aren't available
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        
        info = ydl.extract_info(
            url=f"https://www.youtube.com/watch?v={video_id}", 
            download=True
        )
        channel_name = info.get("channel")
        video_title = info['title']
        video_ext = info['ext']
        channel_name = info.get('channel') # Preferred method

    # If vtt is downloaded, convert it to srt
    video_path = os.path.join(download_path, f"{video_id}.{video_ext}")
    srt_path = None
    try:
        vtt_path = video_path.replace(video_ext, "en.vtt")
        srt_path = convert_vtt_to_srt(vtt_path)
        print("vtt converted to srt")
    except FileNotFoundError:
        vtt_path = None
        print("No subtitles for this video, transcribe it please")
    
    # rename paths    
    paths = {
        'video': video_path,
        'srt': srt_path,
        'vtt': vtt_path
    }
    title = rename_title(video_title, config)
    for key, path in paths.items():
        if path:  # Only rename if path exists
            new_path = path.replace(video_id, f"{channel_name}__{video_id}__{title}")
            os.rename(path, new_path)
            paths[key] = new_path
    
    video_path, srt_path, vtt_path = paths['video'], paths['srt'], paths['vtt']
    print(f"Video downloaded and renamed: {channel_name}__{video_id}__{title}")
    
    return video_path, srt_path, vtt_path


def main():
    parser = argparse.ArgumentParser(description="YouTube Video Downloader")
    parser.add_argument("-y", '--video_id', type=str, help="YouTube video ID to download")
    args = parser.parse_args()

    video_path = download_video(args.video_id)
    print(f"Video downloaded: {video_path}")


if __name__ == "__main__":
    # main()
    ydl_opts = {
        'format': 'worst',
        'writeinfojson': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        
        info = ydl.extract_info(
            url="https://www.youtube.com/watch?v=5z_9sF0bNQE", 
            download=False
        )
        channel_name = info.get("channel")
        video_title = info['title']
        video_ext = info['ext']
        channel_name = info.get('channel') # Preferred method
        uploader = info.get('uploader')
    
    print(channel_name)
    print(uploader)
    print(video_title)
    print(video_ext)
