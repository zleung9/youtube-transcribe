# YouTube Video Downloader and Transcriber

A Python application that automatically monitors a specified YouTube channel for new uploads, downloads the latest video, and generates transcriptions.

## Features
- Monitors a YouTube channel using the YouTube Data API
- Downloads new videos automatically using yt-dlp
- Tracks downloaded videos to prevent duplicates
- Generates SRT subtitle files using Whisper (transcription feature)

## Prerequisites
- Python 3.10 or higher
- YouTube API key
- Channel ID of the YouTube channel to monitor
- uv (Python package installer)

## Installation
1. Clone this repository
2. Install dependencies using uv:
```bash
uv pip install .
```

## Configuration
Update `config.py` with your settings:
- `YOUTUBE_API_KEY`: Your YouTube Data API key
- `CHANNEL_ID`: The YouTube channel ID to monitor
- `DOWNLOAD_PATH`: Directory for downloaded videos (default: './downloads/')

## Usage
Run the script:
```bash
python main.py
```

The script will:
1. Check for new videos in the specified channel
2. Download any new videos found
3. Store downloaded video IDs in `downloaded_videos.txt`

## Project Structure
- `main.py`: Main script orchestrating the workflow
- `downloader.py`: Handles YouTube API interaction and video downloads
- `config.py`: Configuration settings
- `downloaded_videos.txt`: Tracks previously downloaded videos
- `pyproject.toml`: Project dependencies and metadata

## Dependencies
As specified in pyproject.toml:
- google-api-python-client >= 2.158.0
- yt-dlp >= 2024.12.23