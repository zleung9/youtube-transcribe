from flask import Flask, render_template, redirect, url_for, flash  # Added flash import
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_models import Video, Base
from youtube.utils import load_config
from scanner import scan_downloads_folder

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Generate a random secret key for flask session

# Database setup
engine = create_engine('sqlite:///videos.db', echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

@app.route('/')
def index():
    session = Session()
    videos = session.query(Video).order_by(Video.processed_date.desc()).all()
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
    
    # Read transcript if it exists
    transcript_text = ""
    if video and video.transcript_path:
        try:
            with open(video.transcript_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
        except FileNotFoundError:
            transcript_text = "Transcript file not found."
            
    session.close()
    return render_template('video.html', video=video, transcript=transcript_text)

@app.route('/transcript/<video_id>')
def view_transcript(video_id):
    session = Session()
    video = session.query(Video).filter_by(video_id=video_id).first()
    
    if not video or not video.transcript_path:
        return "Transcript not found", 404
        
    try:
        with open(video.transcript_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        return render_template('text_view.html', 
                             title=f"Transcript - {video.title}",
                             content=transcript_text)
    except FileNotFoundError:
        return "Transcript file not found", 404
    finally:
        session.close()

@app.route('/summary/<video_id>')
def view_summary(video_id):
    session = Session()
    video = session.query(Video).filter_by(video_id=video_id).first()
    
    if not video or not video.summary_path:
        return "Summary not found", 404
        
    try:
        with open(video.summary_path, 'r', encoding='utf-8') as f:
            summary_text = f.read()
        return render_template('text_view.html', 
                             title=f"Summary - {video.title}",
                             content=summary_text)
    except FileNotFoundError:
        return "Summary file not found", 404
    finally:
        session.close()

if __name__ == '__main__':
    app.run(
        debug=True, 
        host='127.0.0.1',  # Explicitly bind to localhost
        port=5000,
        threaded=True
    )