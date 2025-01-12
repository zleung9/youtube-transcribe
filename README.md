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
