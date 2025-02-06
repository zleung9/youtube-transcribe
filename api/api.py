from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi_utils.tasks import repeat_every
from typing import List, Dict
import uvicorn
from pydantic import BaseModel
from datetime import datetime, time

app = FastAPI(title="YouTube Monitor API")

class ChannelConfig(BaseModel):
    channel_id: str
    platform: str
    scan_time: time  # Time of day to scan
    enabled: bool = True

class MonitoringService:
    def __init__(self):
        self.config = load_config()
        self.monitors = {}
        self.report = Report(self.config)
        self._initialize_monitors()
    
    def _initialize_monitors(self):
        if 'youtube' in self.config:
            self.monitors['youtube'] = YoutubeMonitor(self.config)
    
    async def process_channel(self, channel: ChannelConfig):
        """Process a single channel's updates"""
        monitor = self.monitors.get(channel.platform)
        if not monitor:
            raise ValueError(f"Unsupported platform: {channel.platform}")
            
        videos = monitor.process_new_videos(channel.channel_id)
        if videos:
            for video in videos:
                await self.process_video(video)
            await self.report.send_update_report(videos)
    
    async def process_video(self, video_info: VideoInfo):
        """Process a single video asynchronously"""
        video = YoutubeVideo()
        video.get(video_info.video_id, download_video=True)
        
        transcriber = Transcriber()
        transcriber.transcribe(video)
        transcriber.process(video)
        transcriber.summarize(video)
        
        self.report.db.add_video(video)

# Initialize the monitoring service
monitor_service = MonitoringService()

@app.on_event("startup")
@repeat_every(seconds=60)  # Check every minute
async def schedule_monitoring():
    """Check if it's time to scan any channels"""
    current_time = datetime.now().time()
    
    for channel in monitor_service.config.get_channels():
        if (channel.enabled and 
            channel.scan_time.hour == current_time.hour and 
            channel.scan_time.minute == current_time.minute):
            await monitor_service.process_channel(channel)

@app.get("/channels/", response_model=List[ChannelConfig])
async def get_channels():
    """Get all monitored channels"""
    return monitor_service.config.get_channels()

@app.post("/channels/")
async def add_channel(channel: ChannelConfig, background_tasks: BackgroundTasks):
    """Add a new channel to monitor"""
    if channel.platform not in monitor_service.monitors:
        raise HTTPException(400, f"Unsupported platform: {channel.platform}")
    
    monitor_service.config.add_channel(channel)
    # Optionally run initial scan
    background_tasks.add_task(monitor_service.process_channel, channel)
    return {"status": "success", "message": "Channel added"}

@app.delete("/channels/{channel_id}")
async def remove_channel(channel_id: str):
    """Remove a channel from monitoring"""
    monitor_service.config.remove_channel(channel_id)
    return {"status": "success", "message": "Channel removed"}

@app.post("/channels/{channel_id}/scan")
async def trigger_scan(channel_id: str, background_tasks: BackgroundTasks):
    """Manually trigger a channel scan"""
    channel = monitor_service.config.get_channel(channel_id)
    if not channel:
        raise HTTPException(404, "Channel not found")
    
    background_tasks.add_task(monitor_service.process_channel, channel)
    return {"status": "success", "message": "Scan initiated"}

@app.get("/videos/")
async def get_videos(
    channel_id: str = None,
    start_date: datetime = None,
    end_date: datetime = None
):
    """Get processed videos with optional filters"""
    return monitor_service.report.db.get_videos(
        channel_id=channel_id,
        start_date=start_date,
        end_date=end_date
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
