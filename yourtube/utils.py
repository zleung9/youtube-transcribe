import json
import re
import os
import shutil
from webvtt import WebVTT
import litellm
import torch
import yt_dlp
import logging

def get_uvicorn_log_config(file_path="logs/uvicorn.log"):
    
    if os.path.exists(file_path):
        os.remove(file_path)

    log_config = {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.FileHandler",
                "filename": file_path
            }
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.error": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False
            }
        }
    }

    return log_config
    


def create_logger(logger_name, log_path = None, append = False, simple_fmt=False):

    # Configure logging
    if not os.path.exists('logs'):
        os.makedirs('logs')

    if not append and os.path.isfile(log_path):
        with open(log_path, 'w') as f: pass
    # If append is False and the file exists, clear the content of the file.

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    if log_path is None:
        handler = logging.StreamHandler() # show log in console
    else:
        handler = logging.FileHandler(log_path) # print log in file
    
    if simple_fmt:
        handler.setFormatter(
            logging.Formatter(
                fmt = "%(message)s"
            )
        )
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt = '%(asctime)s %(levelname)s:  %(message)s',
                datefmt ='%m-%d %H:%M'
            )
        )
    logger.addHandler(handler)

    return logger


def extract_youtube_id(url):
    """Extract video ID from a YouTube URL. It can be a short URL, long URL, or live URL.
    Examples:
    - Regular: https://www.youtube.com/watch?v=ABC123
    - Short: https://youtu.be/ABC123
    - Live: https://www.youtube.com/live/ABC123"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)',
        r'(?:youtube\.com\/embed\/)([\w-]+)',
        r'(?:youtube\.com\/v\/)([\w-]+)',
        r'(?:youtube\.com\/live\/)([\w-]+)(?:\?|$)'  # Added pattern for live URLs
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

    
def get_llm_info(agent):
    """Get model from config.json"""
    config = load_config()
    agent_options = config.get(agent, {})
    title = agent_options.get("model_title")
    max_tokens = agent_options.get("max_tokens")
    temperature = agent_options.get("temperature")
    models = config.get("model", [])

    # Find the model with matching title
    for model in models:
        if model.get("title") == title:
            return (
                model.get("provider"), 
                model.get("name"), 
                model.get("api_key"), 
                max_tokens,
                temperature
            )
            
    raise ValueError(f"Model {title} not found in config.json")

def get_device():
    """Get the device for running Whisper"""
    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    if device in ["cuda", "mps"]:
        print(f"Device detected: {device}")
    return device


def load_config():
    """Load configuration from config.json"""
    config_path = get_config_path()
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("config.json not found. Please create it based on the template.")
        shutil.copy(config_path+'.template', config_path)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in config.json")

def get_config_path():
    """Get the path to the config.json file"""
    return os.path.join(os.path.dirname(__file__), 'config.json')


def convert_vtt_to_srt(vtt_path):
    """Convert VTT file to SRT using webvtt-py and clean the resulting SRT file.
    Cleaning removes duplicate subtitle entries that have multiple lines of text."""
    # Get the output path by replacing .vtt with .srt
    srt_path = vtt_path.replace('vtt', 'srt')
    
    # Convert VTT to SRT
    vtt = WebVTT().read(vtt_path)
    vtt.save_as_srt(srt_path)
    
    # Clean the SRT file to remove duplicate entries
    clean_srt_file(srt_path, srt_path)
    
    # Optionally remove the VTT file
    # os.remove(vtt_path)
    
    return srt_path

def sanitize_filename(filename):
    """Remove or replace invalid characters in filename."""
    # Characters that are not allowed in filenames
    invalid_chars = '<>:"/\\|?*'
    
    # Replace invalid characters with a safe character (underscore)
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    return filename

def rename_title(video_title, config):
    
    try:
        # Use LiteLLM to get response from the specified provider
        response = litellm.completion(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user", 
                    "content": f"Make a concise title out of this: {video_title}, no ':', or '|'"
                }
            ],
            api_key=config.get("openai", {}).get("api_key"),
            max_tokens=4096,
            temperature=0.7
        )
        title = response.choices[0].message.content.strip('"').replace(" ", "_")
        print(title)
    except Exception:
        # title = video_title.strip('"').replace(" ", "_")     
        raise

    
    return title


def get_download_dir(path="downloads/"):
    package_root = os.path.dirname(
        os.path.abspath(__file__)
    )
    download_dir = os.path.join(package_root, path)
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    return download_dir


def get_db_path(path="videos.db"):
    db_path = os.path.join(get_download_dir(), path)
    return db_path


def download_youtube_video(
        path=get_download_dir(),  # Default download path
        video_id=None, # Video ID
        format="wv+ba", # download best audio + worst video
        video=False, # weather download the actual video file
        json=True,
        subtitles=True,
        auto_subtitles=True,
        langs=["en", "zh"]
    ):
    
    ydl_opts = {
            'quiet': False,
            'extract_flat': True,
            'outtmpl': os.path.join(path, f'{video_id}.%(ext)s'),
            'format': format,
            'writeinfojson': json,
            'writesubtitles': subtitles,
            'writeautomaticsub': auto_subtitles,  # Enable auto-generated subtitles if manual ones aren't available'
            'subtitlesformat': 'srt/vtt',
            'subtitleslangs': langs,
            'skip_download': not video
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(
                url=f"https://www.youtube.com/watch?v={video_id}", 
                download=True
            )
        except yt_dlp.utils.DownloadError as e:
            return None
    
    return info

def clean_srt_file(input_file, output_file):
    """
    Clean an SRT file by keeping only subtitle entries with a single line of text.
    Removes entries with two or more lines of text (the duplicates).
    
    Args:
        input_file (str): Path to the input SRT file
        output_file (str): Path to the output SRT file
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split the content by empty lines to get individual subtitle blocks
    subtitle_blocks = content.split('\n\n')
    
    # Keep only subtitle blocks with 4 lines (subtitle number, timestamp, one line of text, and an empty line)
    cleaned_blocks = []
    subtitle_count = 1
    
    for block in subtitle_blocks:
        if not block.strip():  # Skip empty blocks
            continue
            
        lines = block.split('\n')
        
        # A standard single-line subtitle entry has 3 lines:
        # 1. Subtitle number
        # 2. Timestamp
        # 3. One line of text
        if len(lines) == 3:
            # Replace the subtitle number with the new sequence
            lines[0] = str(subtitle_count)
            cleaned_blocks.append('\n'.join(lines))
            subtitle_count += 1
    
    # Join the blocks with empty lines and write to output file
    cleaned_content = '\n\n'.join(cleaned_blocks)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)

def get_language(info, config=None):
    """Get the language of the video from the config and info_json"""
    # if defined in config, return the language
    channel_id = info.get("channel_id", None)
    channel_handle = info.get("uploader_id", None)
    channels_in_config = config.get("youtube", {}).get("channels", [])
    for channel in channels_in_config:
        if channel.get("channel_id") == channel_id or channel.get("channel_handle") == channel_handle:
            return channel.get("language")
    # if not defined in config, get the language from the video info
    if 'subtitles' in info and info['subtitles']: # get the language from subtitles information
        language_codes = [lang_code for lang_code in info['subtitles']]
        for lang_code in language_codes:
            if lang_code.startswith('zh'):
                language = 'zh'
                break
        else:
            language = 'en'
    else:
            language = info.get("language") # if auto, get the language from explicit language information
            if language is None:
                language = config.get("default_lang")
    return language

#  Usage example:
if __name__ == "__main__":
    # driver = webdriver.Chrome()
    # load_youtube_cookies(driver, "/Users/zhuliang/Downloads/youtube_cookies.json")
    config = load_config()
    with open("yourtube/downloads/GU1WRD_v3h8.info.json", "r") as f:
        info = json.load(f)
    language = get_language(info=info, config=config)
    print(language)