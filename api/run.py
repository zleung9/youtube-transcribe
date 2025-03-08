from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_cors import CORS 
import sys
import os
import logging
import glob
from logging.handlers import RotatingFileHandler
import json

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yourtube import Database, Video, Transcriber
from yourtube.utils import get_download_dir, get_db_path, get_config_path, load_config, extract_youtube_id
from yourtube.monitor import YoutubeMonitor
from yourtube.main import process_video_pipeline
from yourtube.async_worker import video_queue

DOWNLOAD_DIR = get_download_dir()
DB_PATH = get_db_path()
print(f"Download directory: {DOWNLOAD_DIR}")
print(f"Database path: {DB_PATH}")

# Database setup
db = Database(db_path=DB_PATH)
monitor = YoutubeMonitor()
transcriber = Transcriber()

# Start the video processing worker
video_queue.start_worker(process_video_pipeline)

app = Flask(__name__)

# Configure logging
if not app.debug:
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Set up file handler
    file_handler = RotatingFileHandler('logs/api.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    app.logger.addHandler(console_handler)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('API startup')

CORS(app, resources={
    r"/*": {
        "origins": ["*"],  # Allow all origins for testing
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})
app.secret_key = os.urandom(24)



def get_file_path(video_id, file_type, language=None):
    """Get file path based on video ID and type."""
    downloads_path = DOWNLOAD_DIR
    
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

def scan_downloads_folder(downloads_path):
    """Scan the downloads folder for video files and update the database."""
    stats = {
        'new_videos': 0,
        'updated_videos': 0,
        'errors': []
    }
    
    # Find all .info.json files in the downloads folder
    json_files = glob.glob(os.path.join(downloads_path, "*.info.json"))
    
    for json_file in json_files:
        try:
            # Extract video_id from filename
            video_id = os.path.basename(json_file).replace('.info.json', '')
            
            # Check if video exists in database
            existing_video = db.get_video(video_id=video_id)
            
            if existing_video:
                # Update existing video
                video = monitor.download(video_id)
                if video:
                    db.update_video(video)
                    stats['updated_videos'] += 1
            else:
                # Add new video
                video = monitor.download(video_id)
                if video:
                    db.add_video(video)
                    stats['new_videos'] += 1
                    
        except Exception as e:
            error_msg = f"Error processing {json_file}: {str(e)}"
            stats['errors'].append(error_msg)
            print(error_msg)
    
    return stats

@app.route('/')
def index():
    sort_by = request.args.get('sort', 'process_date')  # Default to processed_date
    
    if sort_by == 'upload_date':
        videos = db.session.query(Video).order_by(Video.upload_date.desc()).all()
    else:  # processed_date
        videos = db.session.query(Video).order_by(Video.process_date.desc()).all()
    
    if request.headers.get('HX-Request'):  # If it's an AJAX request
        return render_template('video_list.html', videos=videos)
    return render_template('index.html', videos=videos)


#handle AJAX sorting requests
@app.route('/videos')
def get_videos():
    sort_by = request.args.get('sort', 'process_date')
    
    if sort_by == 'upload_date':
        videos = db.session.query(Video).order_by(Video.upload_date.desc()).all()
    else:
        videos = db.session.query(Video).order_by(Video.process_date.desc()).all()
        
    return render_template('index.html', videos=videos)


@app.route('/refresh-library')
def refresh_library():
    downloads_path = DOWNLOAD_DIR
    
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


@app.route('/video/<video_id>', methods=['GET'])
def video_detail(video_id):
    """Get details for a specific video"""
    video = db.get_video(video_id=video_id)
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    # Convert to dictionary for JSON response
    video_data = {
        'video_id': video.video_id,
        'title': video.title,
        'channel': video.channel,
        'upload_date': video.upload_date.isoformat() if video.upload_date else None,
        'process_date': video.process_date.isoformat() if video.process_date else None,
        'has_transcript': bool(video.transcript),
        'has_summary': bool(video.summary),
        'notes': video.notes
    }
    
    return jsonify(video_data)


@app.route('/transcript/<video_id>')
def view_transcript(video_id):
    try:
        video = db.get_video(video_id=video_id)
        
        if not video:
            logging.error(f"Video not found in database: {video_id}")
            return jsonify({"error": "Video not found in database"}), 404
        
        if not video.language:
            logging.error(f"Language not set for video: {video_id}")
            return jsonify({"error": "Video language not set"}), 400
            
        transcript_path = get_file_path(video_id, 'transcript', video.language)
        logging.info(f"Checking transcript at path: {transcript_path}")
        
        if not transcript_path:
            logging.error(f"Invalid transcript path for video: {video_id}")
            return jsonify({"error": "Invalid transcript path"}), 500
            
        if not os.path.exists(transcript_path):
            logging.error(f"Transcript file not found: {transcript_path}")
            return jsonify({"error": "Transcript file not found"}), 404
        
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
            if not transcript_text.strip():
                logging.error(f"Empty transcript file: {transcript_path}")
                return jsonify({"error": "Transcript file is empty"}), 500
            return jsonify({"content": transcript_text})
        except PermissionError:
            logging.error(f"Permission denied reading transcript: {transcript_path}")
            return jsonify({"error": "Permission denied reading transcript file"}), 403
        except Exception as e:
            logging.error(f"Error reading transcript: {str(e)}")
            return jsonify({"error": f"Error reading transcript: {str(e)}"}), 500
    except Exception as e:
        logging.error(f"Unexpected error in view_transcript: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route('/summary/<video_id>')
def view_summary(video_id):
    try:
        video = db.get_video(video_id=video_id)
        
        if not video:
            logging.error(f"Video not found in database: {video_id}")
            return jsonify({"error": "Video not found in database"}), 404
            
        if not video.language:
            logging.error(f"Language not set for video: {video_id}")
            return jsonify({"error": "Video language not set"}), 400
            
        summary_path = get_file_path(video_id, 'summary', video.language)
        logging.info(f"Checking summary at path: {summary_path}")
        
        if not summary_path:
            logging.error(f"Invalid summary path for video: {video_id}")
            return jsonify({"error": "Invalid summary path"}), 500
            
        if not os.path.exists(summary_path):
            logging.error(f"Summary file not found: {summary_path}")
            return jsonify({"error": "Summary file not found"}), 404
        
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary_text = f.read()
            if not summary_text.strip():
                logging.error(f"Empty summary file: {summary_path}")
                return jsonify({"error": "Summary file is empty"}), 500
            return jsonify({"content": summary_text})
        except PermissionError:
            logging.error(f"Permission denied reading summary: {summary_path}")
            return jsonify({"error": "Permission denied reading summary file"}), 403
        except Exception as e:
            logging.error(f"Error reading summary: {str(e)}")
            return jsonify({"error": f"Error reading summary: {str(e)}"}), 500
    except Exception as e:
        logging.error(f"Unexpected error in view_summary: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


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
    try:
        video = db.get_video(video_id=video_id)
        if not video:
            return jsonify({"error": "Video not found"}), 404
            
        summary_path = get_file_path(video_id, 'summary', video.language)
        return jsonify({
            "video_id": video_id,
            "language": video.language,
            "summary_path": summary_path,
            "file_exists": os.path.exists(summary_path),
            "downloads_path": DOWNLOAD_DIR
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/video-content/<video_id>')
def video_content(video_id):
    try:
        video = db.get_video(video_id=video_id)
        if not video:
            return jsonify({
                'transcript': {'error': 'Video not found'},
                'summary': {'error': 'Video not found'}
            }), 404

        # Get transcript
        transcript_text = ""
        transcript_path = get_file_path(video_id, 'transcript', video.language)
        if os.path.exists(transcript_path):
            try:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    transcript_text = f.read()
            except Exception as e:
                transcript_text = f"Error reading transcript: {str(e)}"

        # Get summary
        summary_text = ""
        summary_path = get_file_path(video_id, 'summary', video.language)
        if os.path.exists(summary_path):
            try:
                with open(summary_path, 'r', encoding='utf-8') as f:
                    summary_text = f.read()
            except Exception as e:
                summary_text = f"Error reading summary: {str(e)}"

        return jsonify({
            'transcript': {
                'content': transcript_text,
                'error': None if transcript_text else 'No transcript available'
            },
            'summary': {
                'content': summary_text,
                'error': None if summary_text else 'No summary available'
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/process-video', methods=['POST'])
def process_video(force=True, transcribe=True, process=True, summarize=True):
    
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        # Extract video ID from URL
        video_id = extract_youtube_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        # Check if video is already in queue or being processed
        status = video_queue.get_status(video_id)
        if status in ['queued', 'processing']:
            return jsonify({'success': True, 'status': status, 'video_id': video_id})
        
        # Get basic video info before adding to queue
        video_info = monitor.get_video_info(video_id)
        
        # Add video to processing queue
        video_queue.add_task(
            url=url,
            database=db,
            monitor=monitor,
            transcriber=transcriber,
            force=force,
            transcribe=transcribe,
            process=process,
            summarize=summarize,
            video_id=video_id
        )

        # Return immediately with success status and video info
        return jsonify({
            'success': True, 
            'status': 'queued', 
            'video_id': video_id,
            'title': video_info.get('title', f'Processing: {video_id}'),
            'channel': video_info.get('channel', 'Loading...'),
            'upload_date': video_info.get('upload_date', '')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/video-status/<video_id>', methods=['GET'])
def video_status(video_id):
    status = video_queue.get_status(video_id)
    return jsonify({'status': status or 'unknown'})


@app.route('/delete-video/<video_id>', methods=['DELETE'])
def delete_video(video_id):
    try:
        # Use the database's delete_video method
        success = db.delete_video(video_id=video_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Video not found'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/config', methods=['GET'])
def get_config():
    try:
        config_path = get_config_path()
        
        with open(config_path, 'r') as f:
            config_content = f.read()
        
        return jsonify({'content': config_content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/config', methods=['POST'])
def save_config():
    try:
        config_path = get_config_path()
        
        config_content = request.json.get('content')
        if not config_content:
            return jsonify({'error': 'No content provided'}), 400
        
        # Validate JSON before saving
        try:
            json.loads(config_content)
        except json.JSONDecodeError as e:
            return jsonify({'error': f'Invalid JSON: {str(e)}'}), 400
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def main():
    import webbrowser
    from threading import Timer
    
    # Check if config.json exists, if not create it from template
    load_config();
    
    def open_browser():
        webbrowser.open('http://127.0.0.1:5001/')
    
    # Open browser after a short delay to ensure the server is running
    Timer(1.5, open_browser).start()
    
    # Ensure the worker is stopped when the app exits
    try:
        app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
    finally:
        video_queue.stop_worker()

if __name__ == '__main__':
    main()
