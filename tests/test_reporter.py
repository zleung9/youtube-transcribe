import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import os
from yourtube import YoutubeVideo, Reporter


class TestReporter(unittest.TestCase):
    def setUp(self):
        self.config = {
            'email': {
                'smtp_server': 'smtp.example.com',
                'smtp_port': 587,
                'username': 'test@example.com',
                'password': 'password',
                'recipients': ['recipient@example.com']
            },
            'monitored_platforms': ['youtube'],
            'youtube': {
                'api_key': 'fake_api_key',
                'channels': [
                    {'channel_id': 'UC123', 'check_interval': 3600},
                    {'channel_id': 'UC456', 'check_interval': 3600}
                ]
            }
        }
        self.reporter = Reporter(self.config)

    @patch('yourtube.reporter.SqliteDB')
    @patch('yourtube.reporter.Transcriber')
    def test_process_video(self, mock_transcriber_class, mock_db_class):
        # Create mock instances
        mock_transcriber = MagicMock()
        mock_transcriber_class.return_value = mock_transcriber
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        self.reporter.db = mock_db  # Replace the actual DB with mock
        
        # Create a test video using MagicMock
        test_video = MagicMock(spec=YoutubeVideo)
        current_time = datetime.now()
        
        # Match SQLAlchemy columns from Video class
        test_video.video_id = 'test123'
        test_video.title = 'Test Video'
        test_video.channel_id = 'UC123'
        test_video.channel = 'Test Channel'
        test_video.upload_date = current_time
        test_video.process_date = current_time
        test_video.language = 'en'
        test_video.transcript = True
        test_video.fulltext = True
        test_video.summary = True
        
        # Match Video class properties and instance variables
        test_video.url = 'https://youtube.com/watch?v=test123'
        test_video._default_path = '/tmp'
        test_video._metadata = {
            'video_id': 'test123',
            'title': 'Test Video',
            'video_ext': 'mp4',
            'channel': 'Test Channel',
            'channel_id': 'UC123',
            'language': 'en',
            'upload_date': current_time.strftime('%Y%m%d'),
            'has_video': 1,
            'has_vtt': 1,
            'has_srt': 1
        }
        
        # Mock the file existence checks
        def mock_exists(path):
            return True if path.endswith(('.mp4', '.vtt', '.srt')) else False
        
        # Set up mock returns
        mock_transcriber.transcribe.return_value = "Test transcription"
        mock_transcriber.process.return_value = "Test processing"
        mock_transcriber.summarize.return_value = "Test summary"
        
        # Call the method
        self.reporter._process_video(test_video)
        
        # Verify all expected methods were called
        test_video.get.assert_called_once_with(test_video.video_id, download_video=True)
        mock_transcriber.transcribe.assert_called_once_with(test_video)
        mock_transcriber.process.assert_called_once_with(test_video)
        mock_transcriber.summarize.assert_called_once_with(test_video)
        mock_db.add_video.assert_called_once_with(test_video)

    @patch('yourtube.Reporter._process_video')
    @patch('yourtube.Reporter._send_update_report', new_callable=AsyncMock)
    async def test_process_updates(self, mock_send_report, mock_process_video):
        # Create mock monitor
        mock_monitor = MagicMock()
        
        # Create mock videos
        test_video_1 = MagicMock(spec=YoutubeVideo)
        test_video_1.video_id = 'test123'
        test_video_1.title = 'Test Video 1'
        test_video_1.channel_id = 'UC123'
        test_video_1.channel = 'Test Channel 1'
        test_video_1.upload_date = datetime.now()

        test_video_2 = MagicMock(spec=YoutubeVideo)
        test_video_2.video_id = 'test456'
        test_video_2.title = 'Test Video 2'
        test_video_2.channel_id = 'UC456'
        test_video_2.channel = 'Test Channel 2'
        test_video_2.upload_date = datetime.now()

        mock_monitor.process_new_videos.return_value = [test_video_1, test_video_2]
        
        # Set up mock monitors in the reporter
        self.reporter.monitors = {'youtube': mock_monitor}
        
        # Call the method
        self.reporter.process_updates()
        
        # Verify the monitor was called
        mock_monitor.process_new_videos.assert_called_once()
        
        # Verify _process_video was called for each video
        self.assertEqual(mock_process_video.call_count, 2)
        
        # Verify send_update_report was called with the list of videos
        mock_send_report.assert_called_once()
        
        # Verify the videos passed to send_update_report
        args, _ = mock_send_report.call_args
        self.assertEqual(len(args[0]), 2)  # Should have 2 videos
        self.assertIsInstance(args[0][0], MagicMock)
        self.assertIsInstance(args[0][1], MagicMock)

    def test_process_updates_no_new_videos(self):
        # Create mock monitor that returns no videos
        mock_monitor = MagicMock()
        mock_monitor.process_new_videos.return_value = []
        
        # Set up mock monitors in the reporter
        self.reporter.monitors = {'youtube': mock_monitor}
        
        # Call the method
        self.reporter.process_updates()
        
        # Verify the monitor was called
        mock_monitor.process_new_videos.assert_called_once()

if __name__ == '__main__':
    unittest.main() 