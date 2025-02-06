import unittest
from unittest.mock import patch, MagicMock
from yourtube import Video, YoutubeMonitor

class TestYoutubeMonitor(unittest.TestCase):
    def setUp(self):
        # Sample configuration for the YoutubeMonitor with two channels
        self.config = {
            'youtube': {
                'api_key': 'AIzaSyBmwdkXdNpaD1phF24UdoyrjW-Y2ojJzXs',
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

        # Call the method under test for both channels
        videos_channel_1 = self.monitor.get_latest_videos(self.config['youtube']['channels'][0]['channel_id'], max_results=1)
        videos_channel_2 = self.monitor.get_latest_videos(self.config['youtube']['channels'][1]['channel_id'], max_results=1)

        # Assertions for channel 1
        self.assertEqual(len(videos_channel_1), 1)
        self.assertIsInstance(videos_channel_1[0], Video)
        self.assertEqual(videos_channel_1[0].video_id, 'uk0qGI1T5Kw')
        self.assertEqual(videos_channel_1[0].title, '美股 老实人AMD确实不会烙饼！大跌后续怎么看？GOOG步MSFT后尘！SPOT订阅大超预期！')

        # Assertions for channel 2
        self.assertEqual(len(videos_channel_2), 1)
        self.assertIsInstance(videos_channel_2[0], Video)
        self.assertEqual(videos_channel_2[0].video_id, 'WQV94q2iyFc')
        self.assertEqual(videos_channel_2[0].title, '深度|| 佛祖原本内定的三个取经徒弟分别是谁？')

if __name__ == '__main__':
    unittest.main()
