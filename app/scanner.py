import os
from db_models import Video, Session
import re

def extract_video_info_from_filename(filename):
    """Extract channel name, video ID, and title from filename."""
    pattern = r"(.+)__([a-zA-Z0-9_-]+)__(.+)\.(mp4|srt|txt|vtt)"
    match = re.match(pattern, filename)
    if match:
        channel, video_id, title, ext = match.groups()
        return {
            'channel_name': channel,  # Changed from 'channel' to 'channel_name'
            'video_id': video_id,
            'title': f"{channel}__{video_id}__{title}",
            'ext': ext
        }
    return None

def scan_downloads_folder(downloads_path):
    """Scan downloads folder and update database."""
    session = Session()
    
    # Track statistics
    stats = {
        'new_videos': 0,
        'updated_videos': 0,
        'total_scanned': 0,
        'errors': []
    }
    
    try:
        # Get all files in downloads directory
        for filename in os.listdir(downloads_path):
            stats['total_scanned'] += 1
            
            # Extract info from filename
            info = extract_video_info_from_filename(filename)
            if not info:
                continue
                
            video_id = info['video_id']
            file_path = os.path.join(downloads_path, filename)
            
            try:
                # Check if video exists in database
                video = session.query(Video).filter_by(video_id=video_id).first()
                
                if video is None:
                    # Create new video entry
                    video = Video(
                        video_id=video_id,
                        title=info['title'],
                        channel_name=info['channel_name']  # Changed from 'channel' to 'channel_name'
                    )
                    session.add(video)
                    stats['new_videos'] += 1
                else:
                    stats['updated_videos'] += 1
                    
                # Update paths based on file extension
                if info['ext'] == 'mp4':
                    video.video_path = file_path
                elif info['ext'] == 'srt':
                    video.transcript_path = file_path
                elif info['ext'] == 'txt':
                    video.summary_path = file_path
                    # Optionally read summary text
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            video.summary_text = f.read()
                    except Exception as e:
                        stats['errors'].append(f"Error reading summary file {filename}: {str(e)}")
                        
            except Exception as e:
                stats['errors'].append(f"Error processing file {filename}: {str(e)}")
                continue
        
        session.commit()
        
    except Exception as e:
        stats['errors'].append(f"General error: {str(e)}")
        session.rollback()
    
    finally:
        session.close()
    
    return stats