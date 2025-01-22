from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_cors import CORS 
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os
import logging

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db_models import Video, Base
from youtube.utils import load_config, extract_youtube_id
from youtube.main import process_video_pipeline
from app.scanner import scan_downloads_folder

app = Flask(__name__)
CORS(app) 
app.secret_key = os.urandom(24)

# Database setup
engine = create_engine('sqlite:///videos.db', echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

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
        return jsonify({"error": "Video not found"}), 404
        
    transcript_path = get_file_path(video_id, 'transcript', video.language)
    if not os.path.exists(transcript_path):
        session.close()
        return jsonify({"error": "Transcript not found"}), 404
        
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        return jsonify({"content": transcript_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@app.route('/summary/<video_id>')
def view_summary(video_id):
    session = Session()
    try:
        video = session.query(Video).filter_by(video_id=video_id).first()
        
        if not video:
            logging.error(f"Video not found: {video_id}")
            return jsonify({"error": "Video not found"}), 404
            
        summary_path = get_file_path(video_id, 'summary', video.language)
        logging.info(f"Attempting to read summary from: {summary_path}")
        
        if not os.path.exists(summary_path):
            logging.error(f"Summary file not found: {summary_path}")
            return jsonify({"error": "Summary not found"}), 404
            
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary_text = f.read()
            logging.info(f"Successfully read summary, length: {len(summary_text)}")
            return jsonify({"content": summary_text})
            
    except Exception as e:
        logging.error(f"Error in view_summary: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@app.route('/save-notes/<video_id>', methods=['POST'])
def save_notes(video_id):
    try:
        notes = request.json.get('notes')
        # For now, just print the notes to verify the endpoint is working
        print(f"Saving notes for video {video_id}: {notes}")
        return jsonify({'status': 'success', 'message': 'Notes saved successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/test-paths/<video_id>')
def test_paths(video_id):
    """Debug endpoint to check file paths"""
    session = Session()
    try:
        video = session.query(Video).filter_by(video_id=video_id).first()
        if not video:
            return jsonify({"error": "Video not found"}), 404
            
        summary_path = get_file_path(video_id, 'summary', video.language)
        return jsonify({
            "video_id": video_id,
            "language": video.language,
            "summary_path": summary_path,
            "file_exists": os.path.exists(summary_path),
            "downloads_path": load_config()['paths']['downloads']
        })
    finally:
        session.close()


# Add this new route
@app.route('/process-video', methods=['POST'])
def process_video():
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({'error': 'No URL provided'}), 400

        video_id = extract_youtube_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400

        # Call the processing pipeline
        process_video_pipeline(video_id)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(
        debug=True, 
        host='127.0.0.1',
        port=5000,
        threaded=True
    )