from datetime import datetime
from typing import List, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
import markdown
import os
from yourtube import Database, Video
from yourtube.utils import get_download_dir
import asyncio

REPORT_TEMPLATE_SINGLE = lambda title, url, channel, upload_date, summary: f"""
## [{title}]({url})
**Channel:** {channel}
**Published:** {upload_date.strftime('%Y-%m-%d %H:%M:%S')}

{summary}
#########


"""

class Reporter:
    def __init__(self, config: Dict):
        self.config = config
        self.db = SqliteDB()
        self.email_config = config['email']
        self.download_dir = get_download_dir()
    
    
    def _generate_report_single(self, video: Video) -> str:
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

        return REPORT_TEMPLATE_SINGLE(video.title, video_url, video.channel, video.upload_date, summary_content)


    def _send_email(self, subject: str, content: str):
        """Send email asynchronously"""
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = self.email_config['username']
        msg['To'] = ', '.join(self.email_config['recipients'])
        
        # Convert markdown to HTML
        html_content = markdown.markdown(content)
        msg.attach(MIMEText(html_content, 'html'))
        
        with aiosmtplib.SMTP(
            self.email_config['smtp_server'],
            self.email_config['smtp_port']
        ) as server:
            server.starttls()
            server.login(
                self.email_config['username'],
                self.email_config['password']
            )
            server.send_message(msg)
    

    async def generate_report(self, videos: List[Video]) -> str:
        """Generate full report content from list of videos"""
        if not videos:
            return "## Daily Video Update Report ## \nNo new videos available today."
        # Use asyncio.gather to properly handle multiple async tasks
        summaries = await asyncio.gather(*[self._generate_report_single(video) for video in videos])
        return "\n\n".join(summaries)


    def send_report(self, videos: List[Video]):
        """Generate and send report for new videos"""
        # Add await here since generate_report is async
        report_content = self.generate_report(videos)
        self._send_email(
            subject=f"Video Updates - {datetime.now().strftime('%Y-%m-%d')}",
            content=report_content
        )
