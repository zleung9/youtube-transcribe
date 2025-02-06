from datetime import datetime
from typing import List, Dict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
import aiosmtplib
import markdown
from yourtube import SqliteDB, Video, Transcriber, YoutubeMonitor, BilibiliMonitor


class Reporter:
    def __init__(self, config: Dict):
        self.config = config
        self.db = SqliteDB()
        self.email_config = config['email']
        self.monitors = self._initialize_monitors()
        
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
        """Generate markdown summary for a single video"""
        return f"""
## [{video.title}]({video.url})
**Channel:** {video.channel}
**Published:** {video.upload_date.strftime('%Y-%m-%d %H:%M:%S')}

### Summary
{video.summary}

### Key Insights
{video.insights}
"""

    def _generate_report_content(self, videos: List[Video]) -> str:
        """Generate full report content from list of videos"""
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
    
    def process_updates(self):
        """Check for updates across all monitored channels"""
        new_videos = []
        
        # Check each platform and process all channels for that platform
        for platform, monitor in self.monitors.items():
            channel_videos = monitor.process_new_videos()
            new_videos.extend(channel_videos)
        
        if new_videos:
            # Process videos (download, transcribe, summarize)
            for video in new_videos:
                self._process_video(video)
            
            # Generate and send report
            self._send_update_report(new_videos)
    
    def _process_video(self, video: Video):
        """Process a single video"""
        if isinstance(video, Video):
            video.get(video.video_id, download_video=True)
        
        transcriber = Transcriber()
        transcriber.transcribe(video)
        transcriber.process(video)
        summary = transcriber.summarize(video)
        
        self.db.add_video(video)
    
    def start_scheduler(self):
        """Start the scheduling service"""
        # Schedule updates for each channel
        for platform, monitor in self.monitors.items():
            for channel in self.config[platform]['channels']:
                interval = channel.get('check_interval', 3600)  # default 1 hour
                schedule.every(interval).seconds.do(
                    self.process_updates
                )
        
        # Run the scheduler
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
