# YouTube Video Transcriber

An automated tool that downloads YouTube videos, transcribes them using OpenAI's Whisper, and can generate summaries using OpenAI's GPT API.

## Features

- Automatically downloads new videos from a specified YouTube channel
- Transcribes videos to SRT format using Whisper
- Generates summaries or custom analysis using OpenAI's GPT
- Supports multiple languages (with automatic language detection)
- CPU and GPU (Apple Silicon) support for transcription

## Prerequisites

- Python 3.10 or higher
- OpenAI API key
- YouTube Data API key
- ffmpeg installed on your system

## Installation

1. Clone this repository:
```bash
git clone [your-repo-url]
cd youtube-transcribe
```

2. Install the required packages:
```bash
pip install .
```

3. Set up configuration:
```bash
cp config.json.template config.json
```

4. Edit `config.json` with your settings:
```json
{
    "youtube": {
        "api_key": "YOUR_YOUTUBE_API_KEY",
        "channel_id": "YOUR_CHANNEL_ID"
    },
    "openai": {
        "api_key": "YOUR_OPENAI_API_KEY"
    },
    "whisper": {
        "model": "base",
        "device": "cpu"
    },
    "paths": {
        "downloads": "./downloads",
        "transcripts": "./transcripts"
    }
}
```

## Usage

Run the main script:
```bash
python main.py
```

This will:
1. Check for new videos on the specified YouTube channel
2. Download any new videos
3. Generate transcriptions in SRT format
4. Optionally create summaries using OpenAI GPT

## [TODO]
1. Email service. 
2. Chatbot implementation.
   1. Chat to selected videos.
   2. Chat to a channel.
   3. Implement a vector database.
3. Better audio-to-text transcribe
   1. use better model
4. UI improvement
   1. Sort by processed date
   2. Remove summary and transcript buttons.
   3. Make font smaller for the title.
   4. Dark theme
5. Web deployment.
   1. Process multiple requests uncynchronously.
   2. Website
   3. Login
   4. Payment

[Version]

## Error Handling

- If `config.json` is missing, the program will prompt you to create one from the template
- Network errors during download or API calls are handled gracefully
- Transcription errors are logged and reported

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.