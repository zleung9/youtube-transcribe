import pytest
from unittest.mock import patch, MagicMock
from yourtube import Video, YoutubeMonitor
from datetime import datetime

@pytest.fixture
def youtube_monitor():
    return YoutubeMonitor()

@pytest.fixture
def mock_ydl():
    """Fixture to create a mock YoutubeDL instance"""
    mock = MagicMock()
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = None
    mock.extract_info.return_value = {
        'channel_url': 'https://www.youtube.com/channel/UC9bYDXoFxWC2DQatWI366UA',
        'channel': 'Bohaixiaoli',
        'uploader_id': 'UC9bYDXoFxWC2DQatWI366UA'
    }
    return mock


def test_get_latest_videos(youtube_monitor):
    """Test getting latest videos from a channel"""
    handle = "@bohaixiaoli"
    expected_video_ids = ["xpXFECH5Z3M", "A6LKo6oKbS4", "WQV94q2iyFc"]
    
    videos = youtube_monitor.get_latest_videos(handle, until_date="20250101")
    assert len(videos) == 3
    assert all(video.video_id in expected_video_ids for video in videos)
