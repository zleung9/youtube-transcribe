import os
import argparse
from yourtube import Database, Transcriber
from yourtube.utils import extract_youtube_id
from yourtube.monitor import YoutubeMonitor, BilibiliMonitor
from yourtube.reporter import Reporter
from typing import Dict
import asyncio
import schedule
import time

def initialize_monitors(config: Dict) -> Dict:
    """Initialize monitors for each platform"""
    monitors = {}
    platform_monitors = {
        'youtube': YoutubeMonitor,
        'bilibili': BilibiliMonitor
    }
    for platform in config.get('monitored_platforms', list(platform_monitors.keys())):
        if platform in platform_monitors:
            monitors[platform] = platform_monitors[platform](config)
    return monitors

async def pull_updates(monitors: Dict):
    """Start monitors on the platforms and pull updates to database"""
    for monitor in monitors.values():
        await monitor.pull()

async def process_updates(monitors: Dict):
        """Check for the latest videos in database and create a report. start_date and end_date are in the format of YYYY-MM-DD"""
        new_videos = []
        
        # Check each platform and process all channels for that platform
        for monitor in monitors.values():
            for video_id in monitor.check_updates():
                video = monitor.download(video_id, download_video=True)
                new_videos.append(video)
        
        if not new_videos:
            print("No new videos found")
            return
        
        # Process all videos using a single Transcriber instance
        transcriber = Transcriber()
        for video in new_videos:
            if not video.transcript:
                transcriber.transcribe(video)
            if not video.summary:
                transcriber.summarize(video)
        
        # Generate and send report
        
        # Ensure model is turned off when finished
        transcriber.release_model()


async def run_scheduler(
        args: argparse.Namespace,
        run_immediately=True, 
        daily_time=None,
        reporter: Reporter=None,
        monitors: Dict=None,
        transcriber: Transcriber=None,
        database: Database=None
        ):
        """
        Start the scheduling service
        Args:
            run_immediately (bool): Whether to run once immediately before starting scheduler
            daily_time (str): Time to run daily in 24hr format (e.g., "09:00")
        """
        if run_immediately:
            print("Running immediate check...")
            for platform, monitor in monitors.items():
                new_video_ids =await monitor.check_updates()
                for video_id in new_video_ids:
                    video = database.get_video(video_id=video_id)
                    if video and not args.force:
                        continue
                    video = monitor.download(video_id, download_video=True, download_json=True)
                    database.add_video(video)
            print("Initial check completed.")

        # Schedule updates based on configuration
        if daily_time:
            # Schedule to run at specific time daily
            print(f"Scheduling daily check at {daily_time}")
            schedule.every().day.at(daily_time).do(
                lambda: asyncio.run(process_updates())
            )
        
        # Run the scheduler
        print("Scheduler started...")
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

def process_video_pipeline(url, database, monitor, transcriber, transcribe=False, process=False, summarize=False, force=False, video_id=None):
    """
    Process a video from URL through the pipeline
    
    Args:
        url (str): YouTube URL
        database (Database): Database instance
        monitor (YoutubeMonitor): Monitor instance
        transcriber (Transcriber): Transcriber instance
        transcribe (bool): Whether to transcribe the video
        process (bool): Whether to process the transcript
        summarize (bool): Whether to summarize the transcript
        force (bool): Whether to force processing even if video exists
        video_id (str, optional): Video ID if already extracted
    
    Returns:
        int: 0 on success, non-zero on failure
    """
    if not video_id:
        video_id = extract_youtube_id(url)
    
    video = database.get_video(video_id=video_id)
    if video and not force:
        print(f"Video {video_id} already processed")
        return 0

    # Download and transcribe video flow
    video = monitor.download(video_id)

    if transcribe and not video.transcript:
        print(f"Transcribing video")
        transcriber.load_model(model_name="base")
        _ = transcriber.transcribe(video)
        transcriber.release_model()
    
    if process:
        print(f"Processing SRT file.")
        _ = transcriber.process(video)

    if summarize:
        print(f"Summarizing transcription.")
        _ = transcriber.summarize(video)
    
    # Add to database
    video.update(**transcriber.metadata) 
    database.update_video(video)
    print(f"Successfully downloaded video: {video.title}")
    
    transcriber.release_model()

    return 0

def main():
    parser = argparse.ArgumentParser(description="Transcribe video to SRT format or process an existing SRT file.")
    parser.add_argument("-y", '--youtube_url', type=str, help="YouTube video url to download")
    parser.add_argument("-t", "--transcribe", action="store_true", default=False, help="Whether to transcribe a video file.")
    parser.add_argument("-p", "--process", action="store_true", default=False, help="Whether to process an existing SRT file.")
    parser.add_argument("-s", "--summarize", action="store_true", default=False, help="Whether to summarize the transcription.")
    parser.add_argument("-f", "--force", action="store_true", help="Force to update video even if it exists.")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Display the summary in the terminal after processing.")
    # parser.add_argument("-r", "--report", action="store_true", default=False, help="Create a report of the latest videos.")
    
    args=parser.parse_args()

    process_video_pipeline(
        database=Database(),
        monitor=YoutubeMonitor(),
        transcriber=Transcriber(),
        url=args.youtube_url,
        transcribe=args.transcribe,
        process=args.process,
        summarize=args.summarize,
        force=args.force
    )
 

if __name__ == "__main__":
    main()   
