from datetime import datetime
from typing import List, Dict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
import aiosmtplib
import markdown
import os
from yourtube import SqliteDB, Video, Transcriber, YoutubeMonitor, BilibiliMonitor
from yourtube.utils import get_download_dir, load_config
import asyncio


class Reporter:
    def __init__(self, config: Dict):
        self.config = config
        self.db = SqliteDB()
        self.email_config = config['email']
        self.monitors = self._initialize_monitors()
        self.download_dir = get_download_dir()
        
    def _initialize_monitors(self) -> Dict:
        """Initialize monitors for each platform"""
        monitors = {}
        platform_monitors = {
            'youtube': YoutubeMonitor,
            'bilibili': BilibiliMonitor
        }
        for platform in self.config.get('monitored_platforms', list(platform_monitors.keys())):
            if platform in platform_monitors:
                monitors[platform] = platform_monitors[platform](self.config)
        return monitors
    
    def _generate_video_summary(self, video: Video) -> str:
        """Generate markdown summary for a single video by reading the summary file"""
        # Read summary file
        summary_path = os.path.join(self.download_dir, f"{video.video_id}.md")
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary_content = f.read().strip()
        except FileNotFoundError:
            print(f"Summary file not found for video {video.video_id}")
            summary_content = 'Summary not available'

        # Construct YouTube URL
        video_url = f"https://youtube.com/watch?v={video.video_id}"

        return f"""
## [{video.title}]({video_url})
**Channel:** {video.channel}
**Published:** {video.upload_date.strftime('%Y-%m-%d %H:%M:%S')}

{summary_content}
"""

    def _generate_report_content(self, videos: List[Video]) -> str:
        """Generate full report content from list of videos"""
        if not videos:
            return """
## Daily Video Update Report

No new videos available today.
"""
        summaries = [self._generate_video_summary(video) for video in videos]
        return "\n\n".join(summaries)

    def _create_email_message(self, subject: str, content: str):
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = self.email_config['username']
        msg['To'] = ', '.join(self.email_config['recipients'])
        
        # Convert markdown to HTML
        html_content = markdown.markdown(content)
        msg.attach(MIMEText(html_content, 'html'))
        
        return msg

    async def _send_update_report(self, videos: List[Video]):
        """Generate and send report for new videos"""
        report_content = self._generate_report_content(videos)
        await self._send_email(
            subject=f"Video Updates - {datetime.now().strftime('%Y-%m-%d')}",
            content=report_content
        )
    
    async def _send_email(self, subject: str, content: str):
        """Send email asynchronously"""
        msg = self._create_email_message(subject, content)
        
        async with aiosmtplib.SMTP(
            self.email_config['smtp_server'],
            self.email_config['smtp_port']
        ) as server:
            await server.starttls()
            await server.login(
                self.email_config['username'],
                self.email_config['password']
            )
            await server.send_message(msg)
    
    async def process_updates(self):
        """Check for updates across all monitored channels"""
        new_videos = []
        
        # Check each platform and process all channels for that platform
        for platform, monitor in self.monitors.items():
            channel_videos = monitor.process_new_videos()
            new_videos.extend(channel_videos)
        
        if new_videos:
            # Process all videos using a single Transcriber instance
            transcriber = Transcriber()
            try:
                for video in new_videos:
                    self._process_video(video, transcriber)
                
                # Generate and send report
                await self._send_update_report(new_videos)
            finally:
                # Ensure model is turned off when finished
                transcriber.release_model()
    
    def _process_video(self, video: Video, transcriber: Transcriber):
        """Process a single video"""
        if isinstance(video, Video):
            video.get(video.video_id, download_video=True)
        
        transcriber.transcribe(video)
        transcriber.process(video)
        summary = transcriber.summarize(video)
        
        self.db.add_video(video)
    

    def start_scheduler(self, run_immediately=True, daily_time=None):
        """
        Start the scheduling service
        Args:
            run_immediately (bool): Whether to run once immediately before starting scheduler
            daily_time (str): Time to run daily in 24hr format (e.g., "09:00")
        """
        if run_immediately:
            print("Running immediate check...")
            asyncio.run(self.process_updates())
            print("Initial check completed.")

        # Schedule updates based on configuration
        if daily_time:
            # Schedule to run at specific time daily
            print(f"Scheduling daily check at {daily_time}")
            schedule.every().day.at(daily_time).do(
                lambda: asyncio.run(self.process_updates())
            )
        
        # Run the scheduler
        print("Scheduler started...")
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


if __name__ == "__main__":
    
    async def main():
        config = load_config()
        reporter = Reporter(config)
        
        # For testing, just run once
        print("Starting video check...")
        await reporter.process_updates()
        print("Completed!")
        
        # To run continuously, uncomment this:
        # reporter.start_scheduler()
    
    asyncio.run(main())
