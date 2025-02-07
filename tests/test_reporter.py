import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import os
from yourtube import YoutubeVideo, Reporter, Video
from uuid import uuid4


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
        
        # Create a sample video for tests
        current_time = datetime.now()
        self.sample_video = Video(
            id=uuid4(),
            video_id='test123',
            title='Test Video',
            channel_id='UC123',
            channel='Test Channel',
            upload_date=current_time,
            process_date=current_time,
            language='en',
            transcript=True,
            fulltext=True,
            summary=True
        )
        self.sample_video._metadata = {
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
        self.sample_video._default_path = self.reporter.download_dir

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

    def test_generate_video_summary(self):
        """Test the _generate_video_summary method"""
        # Create a mock summary file
        mock_content = "This is the complete summary content"
        
        with patch('builtins.open', unittest.mock.mock_open(read_data=mock_content)):
            summary = self.reporter._generate_video_summary(self.sample_video)
            
            # Verify the summary contains all required elements
            self.assertIn(self.sample_video.title, summary)
            self.assertIn(f"https://youtube.com/watch?v={self.sample_video.video_id}", summary)
            self.assertIn(self.sample_video.channel, summary)
            self.assertIn(self.sample_video.upload_date.strftime('%Y-%m-%d %H:%M:%S'), summary)
            self.assertIn(mock_content, summary)
            
            # Verify markdown formatting
            self.assertIn('##', summary)  # Title heading
            self.assertIn('**Channel:**', summary)  # Bold text
            self.assertIn('[', summary)  # Link opening bracket
            self.assertIn(']', summary)  # Link closing bracket
            self.assertIn('(', summary)  # URL opening parenthesis
            self.assertIn(')', summary)  # URL closing parenthesis
    
    def test_generate_video_summary_no_file(self):
        """Test generating video summary when file doesn't exist"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            summary = self.reporter._generate_video_summary(self.sample_video)
            self.assertIn('Summary not available', summary)
            self.assertIn(self.sample_video.title, summary)
            self.assertIn(self.sample_video.channel, summary)

    def test_generate_report_content(self):
        """Test the _generate_report_content method"""
        # Create multiple test videos
        current_time = datetime.now()
        test_video_2 = Video(
            id=uuid4(),
            video_id='test456',
            title='Another Test Video',
            channel_id='UC456',
            channel='Another Channel',
            upload_date=current_time,
            process_date=current_time,
            language='en',
            transcript=True,
            fulltext=True,
            summary=True
        )
        test_video_2._metadata = {
            'video_id': 'test456',
            'title': 'Another Test Video',
            'video_ext': 'mp4',
            'channel': 'Another Channel',
            'channel_id': 'UC456',
            'language': 'en',
            'upload_date': current_time.strftime('%Y%m%d'),
            'has_video': 1,
            'has_vtt': 1,
            'has_srt': 1
        }
        test_video_2._default_path = self.reporter.download_dir
        
        videos = [self.sample_video, test_video_2]
        
        # Mock the file reading for both videos
        mock_content_1 = "First video summary content"
        mock_content_2 = "Second video summary content"
        
        def mock_open_file(file_path, *args, **kwargs):
            if self.sample_video.video_id in file_path:
                return unittest.mock.mock_open(read_data=mock_content_1)()
            else:
                return unittest.mock.mock_open(read_data=mock_content_2)()
        
        with patch('builtins.open', mock_open_file):
            # Generate report content
            report_content = self.reporter._generate_report_content(videos)
            
            # Verify report contains summaries for all videos
            for video in videos:
                self.assertIn(video.title, report_content)
                self.assertIn(video.channel, report_content)
                self.assertIn(f"https://youtube.com/watch?v={video.video_id}", report_content)
            
            # Verify summaries are included
            self.assertIn(mock_content_1, report_content)
            self.assertIn(mock_content_2, report_content)
        
        # Test empty video list
        empty_report = self.reporter._generate_report_content([])
        self.assertIn('No new videos available today', empty_report)
        self.assertIn('Daily Video Update Report', empty_report)

    @patch('aiosmtplib.SMTP')
    async def test_send_update_report(self, mock_smtp):
        """Test the _send_update_report method"""
        # Set up mock SMTP instance
        mock_smtp_instance = AsyncMock()
        mock_smtp.return_value = mock_smtp_instance
        mock_smtp_instance.__aenter__.return_value = mock_smtp_instance

        # Create test videos list
        videos = [self.sample_video]
        
        # Mock the report content generation
        with patch.object(self.reporter, '_generate_report_content') as mock_generate:
            mock_generate.return_value = "Test Report Content"
            
            # Call the method
            await self.reporter._send_update_report(videos)
            
            # Verify SMTP connection was established with correct credentials
            mock_smtp_instance.connect.assert_called_once_with(
                hostname=self.config['email']['smtp_server'],
                port=self.config['email']['smtp_port']
            )
            mock_smtp_instance.login.assert_called_once_with(
                self.config['email']['username'],
                self.config['email']['password']
            )
            
            # Verify email was sent with correct parameters
            mock_smtp_instance.send_message.assert_called_once()
            
            # Get the email message that was sent
            sent_message = mock_smtp_instance.send_message.call_args[0][0]
            
            # Verify email contents
            self.assertEqual(sent_message['From'], self.config['email']['username'])
            self.assertEqual(sent_message['To'], ', '.join(self.config['email']['recipients']))
            self.assertIn('Daily Video Update Report', sent_message['Subject'])
            self.assertEqual(sent_message.get_content(), "Test Report Content")

if __name__ == '__main__':
    unittest.main() 