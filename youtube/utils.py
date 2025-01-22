import json
import re
import os
from webvtt import WebVTT
import litellm


def load_config():
    """Load configuration from config.json"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("config.json not found. Please create it based on the template.")
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in config.json")


def convert_vtt_to_srt(vtt_path):
    """Convert VTT file to SRT using webvtt-py."""
    # Get the output path by replacing .vtt with .srt
    srt_path = vtt_path.replace('vtt', 'srt')
    
    # Convert VTT to SRT
    vtt = WebVTT().read(vtt_path)
    vtt.save_as_srt(srt_path)
    
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


def extract_youtube_id(url):
    """Extract video ID from a YouTube URL."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)',
        r'(?:youtube\.com\/embed\/)([\w-]+)',
        r'(?:youtube\.com\/v\/)([\w-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None