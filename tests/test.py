import yt_dlp
from datetime import datetime

def get_latest_videos_until(channel_handle, until_date=None, max_results=1):
    """
    Fetches latest videos from a YouTube channel (by handle) until a specified date.

    Parameters:
        - channel_handle: YouTube channel handle (e.g., "@ChannelHandle")
        - until_date: Cutoff date in "YYYYMMDD" format (e.g., "20240101" for Jan 1, 2024)
        - max_results: Maximum number of videos to check (default: 50)

    Returns:
        - List of videos uploaded until the given date.
    """
    if until_date is None:
        until_date = datetime.now().strftime("%Y%m%d")
    else:
        until_date = datetime.strptime(until_date, "%Y%m%d")
        max_results = 50 
    
    url = f"https://www.youtube.com/{channel_handle}"
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,  # Extract metadata without downloading
        'playlistend': max_results  # Fetch up to `max_results` videos
    }

    filtered_videos = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print(info.keys())
        for video in info['entries']:
            print(video['title'], video.keys())
        # if upload_date and upload_date <= until_date:
            filtered_videos.append({
                'video_id': video['id'],
                'title': video['title'],
                'upload_date': video.get('upload_date'),
            })

        return filtered_videos

# Example usage
channel_handle = "@bohaixiaoli"  # Replace with actual handle
until_date = "20250101"  # Retrieve videos uploaded until January 1, 2024
print(datetime.strptime(until_date, "%Y%m%d"))
latest_videos = get_latest_videos_until(channel_handle, until_date=None)

if not latest_videos:
    print("No videos found before the specified date.")

for idx, video in enumerate(latest_videos[:3], start=1):
    print(f"{video['video_id']}. {video['title']} ({video['upload_date']})")