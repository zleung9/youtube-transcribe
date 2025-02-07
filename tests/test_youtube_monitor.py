import unittest
from unittest.mock import patch, MagicMock
from yourtube import Video, YoutubeMonitor
from datetime import datetime

class TestYoutubeMonitor(unittest.TestCase):
    def setUp(self):
        # Sample configuration for the YoutubeMonitor with two channels
        self.config = {
            'youtube': {
                'api_key': 'test_api_key',
                'channels': [
                    {
                        'channel_id': 'UCFQsi7WaF5X41tcuOryDk8w',
                        'check_interval': 3600
                    },
                    {
                        'channel_id': 'UC9bYDXoFxWC2DQatWI366UA',
                        'check_interval': 3600
                    }
                ]
            }
        }
        self.monitor = YoutubeMonitor(self.config)

    def test_get_latest_videos(self):
        """Test getting latest videos from a channel"""
        # Mock the YoutubeDL extract_info response with timestamp
        current_timestamp = int(datetime.now().timestamp())
        mock_info = {
            'entries': [{
                'id': 'video123',
                'title': 'Test Video',
                'upload_date': '20240101',
                'timestamp': current_timestamp,
                'channel': 'Test Channel',
                'channel_url': 'https://www.youtube.com/channel/UC123',
                'webpage_url': 'https://www.youtube.com/watch?v=video123'
            }]
        }
        
        # Create a context manager mock
        mock_ydl = MagicMock()
        mock_ydl.__enter__.return_value = mock_ydl
        mock_ydl.__exit__.return_value = None
        mock_ydl.extract_info.return_value = mock_info
        
        # Mock the YoutubeDL class to return our mock instance
        with patch('yt_dlp.YoutubeDL', return_value=mock_ydl):
            videos_channel_1 = self.monitor.get_latest_videos('UCFQsi7WaF5X41tcuOryDk8w')
            self.assertEqual(len(videos_channel_1), 1)
            self.assertEqual(videos_channel_1[0].video_id, 'video123')
            
            # Verify the mock was called with correct URL
            mock_ydl.extract_info.assert_called_once()
            call_args = mock_ydl.extract_info.call_args[0][0]
            self.assertIn('UCFQsi7WaF5X41tcuOryDk8w', call_args)

if __name__ == '__main__':
    unittest.main()
