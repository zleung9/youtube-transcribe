import asyncio
import logging
from typing import Dict, List, Optional
from queue import Queue
import threading
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoProcessingQueue:
    def __init__(self):
        self.queue = Queue()
        self.processing_videos = set()  # Set of video_ids currently being processed
        self.worker_thread = None
        self.running = False
        self.status_dict = {}  # Dictionary to store status of each video: 'queued', 'processing', 'completed', 'error'

    def start_worker(self, process_func):
        """Start the worker thread if not already running"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, args=(process_func,))
            self.worker_thread.daemon = True  # Make thread a daemon so it exits when main program exits
            self.worker_thread.start()
            logger.info("Video processing worker started")

    def stop_worker(self):
        """Stop the worker thread"""
        self.running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
            logger.info("Video processing worker stopped")

    def _worker_loop(self, process_func):
        """Worker loop that processes videos from the queue"""
        while self.running:
            try:
                if not self.queue.empty():
                    # Get task from queue
                    task = self.queue.get()
                    video_id = task.get('video_id')
                    
                    # Update status
                    self.status_dict[video_id] = 'processing'
                    self.processing_videos.add(video_id)
                    
                    logger.info(f"Processing video {video_id}")
                    
                    try:
                        # Process the video
                        process_func(**task)
                        # Update status on success
                        self.status_dict[video_id] = 'completed'
                    except Exception as e:
                        # Update status on error
                        self.status_dict[video_id] = 'error'
                        logger.error(f"Error processing video {video_id}: {str(e)}")
                    
                    # Remove from processing set
                    self.processing_videos.remove(video_id)
                    self.queue.task_done()
                else:
                    # Sleep a bit to avoid busy waiting
                    time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error in worker loop: {str(e)}")
                time.sleep(1)  # Sleep to avoid rapid error loops

    def add_task(self, **kwargs):
        """Add a video processing task to the queue"""
        video_id = kwargs.get('video_id')
        if not video_id:
            raise ValueError("video_id is required")
        
        # Check if video is already in queue or being processed
        if video_id in self.processing_videos or video_id in self.status_dict and self.status_dict[video_id] in ['queued', 'processing']:
            logger.info(f"Video {video_id} is already in queue or being processed")
            return False
        
        # Add to queue
        self.status_dict[video_id] = 'queued'
        self.queue.put(kwargs)
        logger.info(f"Added video {video_id} to processing queue")
        return True

    def get_status(self, video_id):
        """Get the status of a video"""
        return self.status_dict.get(video_id, None)

    def get_queue_size(self):
        """Get the current queue size"""
        return self.queue.qsize()

    def get_processing_count(self):
        """Get the number of videos currently being processed"""
        return len(self.processing_videos)

# Create a global instance of the queue
video_queue = VideoProcessingQueue() 