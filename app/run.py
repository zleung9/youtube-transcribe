from flask import Flask, render_template, redirect, url_for, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db_models import Video, Base
from youtube.utils import load_config
from app.scanner import scan_downloads_folder

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database setup
engine = create_engine('sqlite:///videos.db', echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def get_file_path(video_id, file_type, language=None):
    """Get file path based on video ID and type."""
    config = load_config()
    downloads_path = config['paths']['downloads']
    
    if file_type == 'video':
        return os.path.join(downloads_path, f"{video_id}.mp4")
    elif file_type == 'transcript':
        return os.path.join(downloads_path, f"{video_id}.{language}.srt")
    elif file_type == 'summary':
        return os.path.join(downloads_path, f"{video_id}.{language}.md")
    elif file_type == 'json':
        return os.path.join(downloads_path, f"{video_id}.info.json")
    return None

@app.route('/')
def index():
    session = Session()
    videos = session.query(Video).order_by(Video.date.desc()).all()
    session.close()
    return render_template('index.html', videos=videos)

@app.route('/refresh-library')
def refresh_library():
    config = load_config()
    downloads_path = config['paths']['downloads']
    
    try:
        stats = scan_downloads_folder(downloads_path)
        
        # Create success message
        success_msg = f"Library refreshed! Found {stats['new_videos']} new videos, updated {stats['updated_videos']} existing videos."
        
        # Add errors if any
        if stats.get('errors'):
            success_msg += f"\nWarnings: {len(stats['errors'])} errors occurred."
            for error in stats['errors']:
                flash(error, "warning")
                
        flash(success_msg, "success")
        
    except Exception as e:
        flash(f"Error refreshing library: {str(e)}", "error")
    
    return redirect(url_for('index'))

@app.route('/video/<video_id>')
def video_detail(video_id):
    session = Session()
    video = session.query(Video).filter_by(video_id=video_id).first()
    
    if not video:
        session.close()
        return "Video not found", 404
    
    # Get transcript if it exists
    transcript_text = ""
    transcript_path = get_file_path(video_id, 'transcript', video.language)
    if os.path.exists(transcript_path):
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
        except Exception:
            transcript_text = "Error reading transcript."
            
    session.close()
    return render_template('video.html', video=video, transcript=transcript_text)

@app.route('/transcript/<video_id>')
def view_transcript(video_id):
    session = Session()
    video = session.query(Video).filter_by(video_id=video_id).first()
    
    if not video:
        session.close()
        return "Video not found", 404
        
    transcript_path = get_file_path(video_id, 'transcript', video.language)
    if not os.path.exists(transcript_path):
        session.close()
        return "Transcript not found", 404
        
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        return render_template('text_view.html', 
                             title=f"Transcript - {video.title}",
                             content=transcript_text)
    except Exception as e:
        return f"Error reading transcript: {str(e)}", 500
    finally:
        session.close()

@app.route('/summary/<video_id>')
def view_summary(video_id):
    session = Session()
    video = session.query(Video).filter_by(video_id=video_id).first()
    
    if not video:
        session.close()
        return "Video not found", 404
        
    summary_path = get_file_path(video_id, 'summary', video.language)
    if not os.path.exists(summary_path):
        session.close()
        return "Summary not found", 404
        
    try:
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary_text = f.read()
        return render_template('text_view.html', 
                             title=f"Summary - {video.title}",
                             content=summary_text)
    except Exception as e:
        return f"Error reading summary: {str(e)}", 500
    finally:
        session.close()

if __name__ == '__main__':
    app.run(
        debug=True, 
        host='127.0.0.1',
        port=5000,
        threaded=True
    )