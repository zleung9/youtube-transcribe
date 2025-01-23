import os
from googleapiclient.discovery import build
import yt_dlp
from youtube.utils import load_config, convert_vtt_to_srt
import argparse

def get_video_info(video_id, download=False, path=None, format='worst'):
    '''
    Download a YouTube video using yt-dlp library.
    Parameters:
    - video_id: str, YouTube video ID
    - download: bool, whether to download the video
    - path: str, path to save the video
    - quality: str, quality of the video to download
    Returns:
    - metadata: dict, metadata of the video
    '''
    if path is None:
        raise ValueError("Path cannot be None when downloading videos")
        
    video_path = os.path.join(path, f'{video_id}.%(ext)s')
    ydl_opts = {
        'quiet': False,
        'extract_flat': True,
        'outtmpl': video_path,
        'format': format,
        'writeinfojson': True,
        'writesubtitles': True,
        'writeautomaticsub': True,  # Enable auto-generated subtitles if manual ones aren't available'
        'subtitleslangs': ['en', "zh"]
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            url=f"https://www.youtube.com/watch?v={video_id}", 
            download=download
        )
    
    video_title = info.get('title', 'Untitled')
    video_ext = info['ext']
    language = info.get('language', 'zh')
    
    # Set the actual video path with the correct extension
    actual_video_path = os.path.join(path, f'{video_id}.{video_ext}')
    
    metadata = {
        'video_title': video_title,
        'video_ext': video_ext,
        'video_path': actual_video_path if download else None,
        'language': language
    }

    return metadata



def get_latest_video_id(config):

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


def download_video(video_id, config=load_config()):
    download_path = config['paths']['downloads']
    metadata = get_video_info(video_id, download=True, path=download_path)
    video_ext = metadata['video_ext']
    language = metadata['language']

    # If vtt is downloaded, convert it to srt
    video_path = metadata['video_path']
    srt_path = None
    try:
        vtt_path = video_path.replace(video_ext, f"{language}.vtt")
        srt_path = convert_vtt_to_srt(vtt_path)
        print(f"vtt converted to srt: {srt_path}")
    except FileNotFoundError:
        # even vtt is not available, we still need to keep path, usually this is the case for "zh"
        print("No subtitles for this video, transcribe it please")
    
    # rename paths    
    metadata.update(
        {
            'video_path': video_path,
            'srt_path': srt_path,
            'vtt_path': vtt_path
        }
    )

    return metadata


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
