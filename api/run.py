import sys
import os
import logging
import json
import glob
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Form, Query, Path
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from yourtube import Database, Video, Transcriber
from yourtube.utils import get_download_dir, get_db_path, get_config_path, load_config, extract_youtube_id
from yourtube.monitor import YoutubeMonitor
from yourtube.main import process_video_pipeline
from yourtube.async_worker import video_queue
# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# global variables setup: database, monitor, transcriber, config, video_queue
DOWNLOAD_DIR = get_download_dir()
DB_PATH = get_db_path()
print(f"Download directory: {DOWNLOAD_DIR}")
print(f"Database path: {DB_PATH}")

config = load_config() #check if config.json exists, if not create it from template
db = Database(db_path=DB_PATH)
monitor = YoutubeMonitor(config=config)
transcriber = Transcriber(config=config)
video_queue.start_worker(process_video_pipeline) # Start the video processing worker

# FastAPI app setup
app = FastAPI(title="YourTube")

# Configure logging
if not os.path.exists('logs'):
    os.makedirs('logs')

# Set up file handler
file_handler = RotatingFileHandler('logs/api.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)

# Set up console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Configure root logger
logger = logging.getLogger()
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)
logger.info('API startup')

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Mount static files
app.mount("/static", StaticFiles(directory="api/static"), name="static")

# Templates
templates = Jinja2Templates(directory="api/templates")

# Pydantic models for request/response
class VideoResponse(BaseModel):
    id: str
    video_id: str
    title: str
    channel: str
    channel_id: Optional[str] = None
    upload_date: str
    process_date: Optional[str] = None
    language: Optional[str] = None
    transcript: Optional[bool] = False
    fulltext: Optional[bool] = False
    summary: Optional[bool] = False
    status: Optional[str] = None
    
    @classmethod
    def from_video(cls, video):
        """Create a VideoResponse from a Video object"""
        video_dict = video.to_dict()
        return cls(
            id=video_dict['id'],
            video_id=video_dict['video_id'],
            title=video_dict['title'],
            channel=video_dict['channel'],
            channel_id=video_dict['channel_id'],
            upload_date=video_dict['upload_date'] or '',
            process_date=video_dict['process_date'],
            language=video_dict['language'],
            transcript=video_dict['transcript'],
            fulltext=video_dict['fulltext'],
            summary=video_dict['summary'],
            status=None  # Status is not part of the Video model
        )

class ProcessVideoResponse(BaseModel):
    success: bool
    status: str
    video_id: str
    title: str
    channel: str
    upload_date: str
    
    @classmethod
    def from_dict(cls, data):
        """Create a ProcessVideoResponse from a dictionary"""
        return cls(
            success=data.get('success', True),
            status=data.get('status', 'queued'),
            video_id=data.get('video_id', ''),
            title=data.get('title', ''),
            channel=data.get('channel', ''),
            upload_date=data.get('upload_date', '')
        )

class VideoStatusResponse(BaseModel):
    status: str
    
    @classmethod
    def from_status(cls, status):
        """Create a VideoStatusResponse from a status string"""
        return cls(status=status or 'unknown')

class DeleteVideoResponse(BaseModel):
    success: bool
    
    @classmethod
    def from_success(cls, success):
        """Create a DeleteVideoResponse from a success boolean"""
        return cls(success=success)

class ProcessVideoRequest(BaseModel):
    url: str
    force: bool = True
    transcribe: bool = True
    process: bool = True
    summarize: bool = True

class NotesRequest(BaseModel):
    notes: str

class ContentSection(BaseModel):
    content: str = ""
    error: str = ""

class VideoContentResponse(BaseModel):
    transcript: ContentSection
    summary: ContentSection
    
    @classmethod
    def from_content(cls, transcript_text: str = "", summary_text: str = "", transcript_error: str = "", summary_error: str = ""):
        """Create a VideoContentResponse from transcript and summary content"""
        return cls(
            transcript=ContentSection(content=transcript_text, error=transcript_error),
            summary=ContentSection(content=summary_text, error=summary_error)
        )

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

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, sort: str = Query("process_date", description="Sort videos by process_date or upload_date")):
    if sort == 'upload_date':
        videos = db.session.query(Video).order_by(Video.upload_date.desc()).all()
    else:  # processed_date
        videos = db.session.query(Video).order_by(Video.process_date.desc()).all()
    
    return templates.TemplateResponse("index.html", {"request": request, "videos": videos})

@app.get("/videos", response_class=HTMLResponse)
async def get_videos(request: Request, sort: str = Query("process_date", description="Sort videos by process_date or upload_date")):
    if sort == 'upload_date':
        videos = db.session.query(Video).order_by(Video.upload_date.desc()).all()
    else:
        videos = db.session.query(Video).order_by(Video.process_date.desc()).all()
        
    return templates.TemplateResponse("index.html", {"request": request, "videos": videos})

@app.get("/refresh-library", response_class=RedirectResponse)
async def refresh_library():
    downloads_path = DOWNLOAD_DIR
    
    try:
        stats = scan_downloads_folder(downloads_path)
        
        # Create success message
        success_msg = f"Library refreshed! Found {stats['new_videos']} new videos, updated {stats['updated_videos']} existing videos."
        
        # Add errors if any
        if stats.get('errors'):
            success_msg += f"\nWarnings: {len(stats['errors'])} errors occurred."
            for error in stats['errors']:
                # In FastAPI, we can't use flash messages directly, so we'll use a different approach
                # For now, we'll just log the errors
                logger.warning(error)
                
        logger.info(success_msg)
        
    except Exception as e:
        logger.error(f"Error refreshing library: {str(e)}")
    
    return RedirectResponse(url="/", status_code=303)

@app.get("/video/{video_id}", response_model=VideoResponse)
async def video_detail(video_id: str = Path(..., description="The ID of the video to retrieve")):
    """Get details for a specific video"""
    video = db.get_video(video_id=video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Convert to VideoResponse model using the class method
    return VideoResponse.from_video(video)

@app.get("/transcript/{video_id}", response_model=Dict[str, str])
async def view_transcript(video_id: str = Path(..., description="The ID of the video to retrieve transcript for")):
    try:
        video = db.get_video(video_id=video_id)
        
        if not video:
            logger.error(f"Video not found in database: {video_id}")
            raise HTTPException(status_code=404, detail="Video not found in database")
        
        if not video.language:
            logger.error(f"Language not set for video: {video_id}")
            raise HTTPException(status_code=400, detail="Video language not set")
            
        transcript_path = get_file_path(video_id, 'transcript', video.language)
        logger.info(f"Checking transcript at path: {transcript_path}")
        
        if not transcript_path:
            logger.error(f"Invalid transcript path for video: {video_id}")
            return {"content": ""}  # Return empty content instead of error
            
        if not os.path.exists(transcript_path):
            logger.error(f"Transcript file not found: {transcript_path}")
            return {"content": ""}  # Return empty content instead of error
        
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
            if not transcript_text.strip():
                logger.error(f"Empty transcript file: {transcript_path}")
                return {"content": ""}  # Return empty content
            return {"content": transcript_text}
        except Exception as e:
            logger.error(f"Error reading transcript: {str(e)}")
            return {"content": ""}  # Return empty content instead of error
    except Exception as e:
        logger.error(f"Unexpected error in view_transcript: {str(e)}")
        return {"content": ""}  # Return empty content instead of error

@app.get("/summary/{video_id}", response_model=Dict[str, str])
async def view_summary(video_id: str = Path(..., description="The ID of the video to retrieve summary for")):
    try:
        video = db.get_video(video_id=video_id)
        
        if not video:
            logger.error(f"Video not found in database: {video_id}")
            raise HTTPException(status_code=404, detail="Video not found in database")
            
        if not video.language:
            logger.error(f"Language not set for video: {video_id}")
            raise HTTPException(status_code=400, detail="Video language not set")
            
        summary_path = get_file_path(video_id, 'summary', video.language)
        logger.info(f"Checking summary at path: {summary_path}")
        
        if not summary_path:
            logger.error(f"Invalid summary path for video: {video_id}")
            return {"content": ""}  # Return empty content instead of error
            
        if not os.path.exists(summary_path):
            logger.error(f"Summary file not found: {summary_path}")
            return {"content": ""}  # Return empty content instead of error
        
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary_text = f.read()
            if not summary_text.strip():
                logger.error(f"Empty summary file: {summary_path}")
                return {"content": ""}  # Return empty content
            return {"content": summary_text}
        except Exception as e:
            logger.error(f"Error reading summary: {str(e)}")
            return {"content": ""}  # Return empty content instead of error
    except Exception as e:
        logger.error(f"Unexpected error in view_summary: {str(e)}")
        return {"content": ""}  # Return empty content instead of error

@app.post("/save-notes/{video_id}", response_model=Dict[str, str])
async def save_notes(video_id: str = Path(..., description="The ID of the video to save notes for"), notes_request: NotesRequest = None):
    try:
        notes = notes_request.notes if notes_request else ""
        # For now, just print the notes to verify the endpoint is working
        print(f"Saving notes for video {video_id}: {notes}")
        return {'status': 'success', 'message': 'Notes saved successfully'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-paths/{video_id}", response_model=Dict[str, Any])
async def test_paths(video_id: str = Path(..., description="The ID of the video to test paths for")):
    """Debug endpoint to check file paths"""
    try:
        video = db.get_video(video_id=video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
            
        summary_path = get_file_path(video_id, 'summary', video.language)
        return {
            "video_id": video_id,
            "language": video.language,
            "summary_path": summary_path,
            "file_exists": os.path.exists(summary_path),
            "downloads_path": DOWNLOAD_DIR
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video-content/{video_id}", response_model=VideoContentResponse)
async def video_content(video_id: str = Path(..., description="The ID of the video to retrieve content for")):
    try:
        video = db.get_video(video_id=video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        # Get transcript
        transcript_text = ""
        transcript_error = ""
        transcript_path = get_file_path(video_id, 'transcript', video.language)
        if os.path.exists(transcript_path):
            try:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    transcript_text = f.read()
            except Exception as e:
                logger.error(f"Error reading transcript: {str(e)}")
                transcript_error = str(e)

        # Get summary
        summary_text = ""
        summary_error = ""
        summary_path = get_file_path(video_id, 'summary', video.language)
        if os.path.exists(summary_path):
            try:
                with open(summary_path, 'r', encoding='utf-8') as f:
                    summary_text = f.read()
            except Exception as e:
                logger.error(f"Error reading summary: {str(e)}")
                summary_error = str(e)

        return VideoContentResponse.from_content(
            transcript_text=transcript_text,
            summary_text=summary_text,
            transcript_error=transcript_error,
            summary_error=summary_error
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in video_content: {str(e)}")
        return VideoContentResponse.from_content(
            transcript_error="Failed to load content",
            summary_error="Failed to load content"
        )

@app.post("/process-video", response_model=ProcessVideoResponse)
async def process_video(request: ProcessVideoRequest):
    global config
    global transcriber
    global monitor
    global db
    global video_queue
        
    url = request.url
    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")
    
    try:
        # Extract video ID from URL
        video_id = extract_youtube_id(url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        # Check if video is already in queue or being processed
        status = video_queue.get_status(video_id)
        if status in ['queued', 'processing']:
            return ProcessVideoResponse.from_dict({
                'success': True,
                'status': status,
                'video_id': video_id,
                'title': f'Processing: {video_id}',
                'channel': 'Loading...',
                'upload_date': ''
            })
        
        # Get basic video info before adding to queue
        video_info = monitor.get_video_info(video_id)
        
        # Add video to processing queue
        video_queue.add_task(
            config=config,
            url=url,
            database=db,
            monitor=monitor,
            transcriber=transcriber,
            force=request.force,
            transcribe=request.transcribe,
            process=request.process,
            summarize=request.summarize,
            video_id=video_id,
            is_last=False
        )

        # Return immediately with success status and video info
        return ProcessVideoResponse.from_dict({
            'success': True,
            'status': 'queued',
            'video_id': video_id,
            'title': video_info.get('title', f'Processing: {video_id}'),
            'channel': video_info.get('channel', 'Loading...'),
            'upload_date': video_info.get('upload_date', '')
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video-status/{video_id}", response_model=VideoStatusResponse)
async def video_status(video_id: str = Path(..., description="The ID of the video to check status for")):
    status = video_queue.get_status(video_id)
    return VideoStatusResponse.from_status(status)

@app.delete("/delete-video/{video_id}", response_model=DeleteVideoResponse)
async def delete_video(video_id: str = Path(..., description="The ID of the video to delete")):
    try:
        # Use the database's delete_video method
        success = db.delete_video(video_id=video_id)
        
        if success:
            return DeleteVideoResponse.from_success(True)
        else:
            raise HTTPException(status_code=404, detail="Video not found")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config", response_model=Dict[str, str])
async def get_config():
    try:
        config_path = get_config_path()
        
        with open(config_path, 'r') as f:
            config_content = f.read()
        
        return {'content': config_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config", response_model=Dict[str, bool])
async def save_config(request: Request):
    try:
        global config  # Reference the global config variable
        config_path = get_config_path()
        
        config_data = await request.json()
        config_content = config_data.get('content')
        if not config_content:
            raise HTTPException(status_code=400, detail="No content provided")
        
        # Validate JSON before saving
        try:
            new_config = json.loads(config_content)
            # Update the global config variable
            config = new_config
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # Log that config was updated
        logger.info("Configuration updated successfully")
        
        return {'success': True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/script/{video_id}", response_model=Dict[str, str])
async def view_script(video_id: str = Path(..., description="The ID of the video to retrieve script for")):
    try:
        video = db.get_video(video_id=video_id)
        
        if not video:
            logger.error(f"Video not found in database: {video_id}")
            raise HTTPException(status_code=404, detail="Video not found in database")
        
        if not video.language:
            logger.error(f"Language not set for video: {video_id}")
            raise HTTPException(status_code=400, detail="Video language not set")
            
        # Construct the path to the processed.txt file
        script_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{video.language}.processed.txt")
        logger.info(f"Checking script at path: {script_path}")
        
        if not os.path.exists(script_path):
            logger.error(f"Script file not found: {script_path}")
            return {"content": ""}  # Return empty content instead of error
        
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                script_text = f.read()
            if not script_text.strip():
                logger.error(f"Empty script file: {script_path}")
                return {"content": ""}  # Return empty content
            return {"content": script_text}
        except Exception as e:
            logger.error(f"Error reading script: {str(e)}")
            return {"content": ""}  # Return empty content instead of error
    except Exception as e:
        logger.error(f"Unexpected error in view_script: {str(e)}")
        return {"content": ""}  # Return empty content instead of error

def main():
    import webbrowser
    from threading import Timer
    import uvicorn

    def open_browser():
        webbrowser.open('http://127.0.0.1:5001/')
    
    # Open browser after a short delay to ensure the server is running
    Timer(1.5, open_browser).start()
    
    # Ensure the worker is stopped when the app exits
    try:
        uvicorn.run(app, host="0.0.0.0", port=5001, reload=False)
    finally:
        video_queue.stop_worker()

if __name__ == '__main__':
    main()
