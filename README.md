# YouTube Channel Monitor (Pre-release)

This tool monitors selected YouTube channels and generates summary reports of the latest videos. The key benefit is helping you decide whether to watch videos by reading AI-generated summaries first, saving you valuable time.

While there are similar products available (often paid), this solution offers unique values:
- It provides a daily report of concise summaries of channels' latest update that can replace watching entire videos in many cases. 
- It can get transcript for videos that does not have a subtitle, e.g. videos in Chinese. If you want to read the summary of a video in Chinese, this is the app you are looking for.

The application includes a web-based user interface. Email notification functionality is currently under development. For now, videos of interest must be manually added to the database.


## Installation

1. Clone this repository:
```bash
git clone https://github.com/zleung9/youtube-transcribe.git
cd youtube-transcribe
```

2. Activate a Python environment using conda or venv:

   **Using conda:**
   ```bash
   conda create -n youtube-transcribe python=3.10
   conda activate youtube-transcribe
   ```

   **Using venv:**
   ```bash
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```


3. Install the required packages. 
```bash
pip install -e . -r requirements.txt
```

4. Set up configuration:
```bash
cp config.json.template config.json
```

Edit `config.json` with your settings:
```json
{
    "model": [
        {
            "title": "openai-gpt-4o",
            "provider": "openai",
            "name": "gpt-4o",
            "api_key": "YOUR_OPENAI_API_KEY"
        },
        {   
            "title": "anthropic-claude-3.5-sonnet",
            "provider": "anthropic",
            "name": "claude-3-5-sonnet-20240620",
            "api_key": "YOUR_ANTHROPIC_API_KEY"
        }
    ],
    "summarizer": {
        "model_title": "anthropic-claude-3.5-sonnet", # by default
        "max_tokens": 4096,
        "temperature": 0.8
    },
}
```

The configuration file supports multiple AI models for summarization, YouTube channel monitoring with customizable check intervals, and email notification settings. You'll need to provide your own API keys for the services you plan to use.

## Usage

Run the main script. The command is `yourtube` with an "r". 
```bash
yourtube
```

This will open a web app in your default browser. For each video the app will fetch subtitles, summarize the content and store it in a sql database. 

Most of the time, videos spoken in Chinese doesn't have a subtitle. The app will download the video and transcribe using Whisper to get the subtitles. The downloaded video is then deleted upon the completion of transcription.


Here is a simple demo: 
[![Demo Video](https://img.youtube.com/vi/wu59USebe3g/maxresdefault.jpg)](https://youtu.be/wu59USebe3g)