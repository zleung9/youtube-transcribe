import os
import json
from datetime import datetime
from app.db_models import Video, Session

def get_video_info_from_json(json_path):
    """Extract video information from JSON file."""
    try:
        _ = open(json_path.replace('.info.json', '.en.srt'), 'r')
        language = 'en'
    except FileNotFoundError:
        try:
            _ = open(json_path.replace('.info.json', '.zh.srt'), 'r')
            language = 'zh'
        except FileNotFoundError:
            language = None

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {
            'video_id': data.get('id'),
            'title': data.get('title'),
            'channel': data.get('channel'),
            'channel_id': data.get('channel_id'),  # Added channel_id extraction
            'language': language,  # Default to 'en' if not specified
            'date': data.get('upload_date')
        }
    except Exception:
        return None

def get_associated_files(video_id, base_path):
    """Get all associated files for a video ID."""
    files = {
        'video': None,
        'transcripts': [],
        'summaries': [],
        'json': None
    }

    for filename in os.listdir(base_path):
        if filename.startswith(video_id):
            filepath = os.path.join(base_path, filename)
            if filename == f"{video_id}.mp4":
                files['video'] = filepath
            elif filename.endswith('.srt'):
                lang = filename.replace(f"{video_id}.", '').replace('.srt', '')
                files['transcripts'].append((lang, filepath))
            elif filename.endswith('.md'):
                lang = filename.replace(f"{video_id}.", '').replace('.md', '')
                files['summaries'].append((lang, filepath))
            elif filename.endswith('.info.json'):
                files['json'] = filepath

    return files

def scan_downloads_folder(downloads_path, video_ids=[]):
    """
    Scan downloads folder and update database.
    If video_ids is provided, only scan those videos.
    """
    session = Session()

    stats = {
        'new_videos': 0,
        'updated_videos': 0,
        'total_scanned': 0,
        'errors': []
    }

    try:
        # Look for JSON files first
        json_files = [f for f in os.listdir(downloads_path) if f.endswith('.info.json')]

        for json_file in json_files:
            # If video_ids is provided, skip if not in list
            if video_ids and json_file.replace('.info.json', '') not in video_ids:
                continue
            stats['total_scanned'] += 1
            video_id = json_file.replace('.info.json', '')
            json_path = os.path.join(downloads_path, json_file)


            try:
                # Get info from JSON
                info = get_video_info_from_json(json_path)
                if not info:
                    stats['errors'].append(f"Error reading JSON file {json_file}")
                    continue

                # Get all associated files
                files = get_associated_files(video_id, downloads_path)

                # Check if video exists in database
                video = session.query(Video).filter_by(video_id=video_id).first()

                if video is None:
                    # Create new video entry
                    video = Video(
                        video_id=video_id,
                        title=info['title'],
                        channel=info['channel'],
                        channel_id=info['channel_id'],  # Added channel_id
                        language=info['language'],
                        date=datetime.strptime(info['date'], '%Y%m%d').date()
                    )
                    session.add(video)
                    stats['new_videos'] += 1
                else:
                    # Update existing video information
                    video.title = info['title']
                    video.channel = info['channel']
                    video.channel_id = info['channel_id']  # Update channel_id
                    video.language = info['language']
                    stats['updated_videos'] += 1
                    video.date = datetime.strptime(info['date'], '%Y%m%d').date()

                # Update video path
                if files['video']:
                    video.video_path = files['video']

                # Update transcript and summary flags based on existing files
                video.transcript = len(files['transcripts']) > 0
                video.summary = len(files['summaries']) > 0

            except Exception as e:
                stats['errors'].append(f"Error processing video {video_id}: {str(e)}")
                continue
        
        session.commit()

    except Exception as e:
        stats['errors'].append(f"General error: {str(e)}")
        session.rollback()
    
    finally:
        session.close()
    
    return stats