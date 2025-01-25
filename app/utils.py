import os
from youtube.utils import load_config

def get_file_path(video_id, file_type, language=None):
    """Get file path based on video ID and type."""
    config = load_config()
    downloads_path = config['paths']['downloads']
    
    print(f"Getting path for video: {video_id}, type: {file_type}, language: {language}")  # Debug print
    
    if file_type == 'video':
        path = os.path.join(downloads_path, f"{video_id}.mp4")
    elif file_type == 'transcript':
        path = os.path.join(downloads_path, f"{video_id}.{language}.srt")
    elif file_type == 'summary':
        path = os.path.join(downloads_path, f"{video_id}.{language}.md")
    elif file_type == 'json':
        path = os.path.join(downloads_path, f"{video_id}.info.json")
    else:
        return None
        
    print(f"Constructed path: {path}")  # Debug print
    print(f"File exists: {os.path.exists(path)}")  # Debug print
    return path