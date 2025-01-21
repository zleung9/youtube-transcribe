import yt_dlp

def get_youtube_subscriptions():
    # Configure yt-dlp options
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
    }

    # Create yt-dlp object
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Fetch subscription feed
            result = ydl.extract_info(
                'https://www.youtube.com/feed/subscriptions',
                download=False
            )
            print()
            # Print channel information
            if 'entries' in result:
                for entry in result['entries']:
                    print(f"Channel: {entry.get('uploader', 'Unknown')}")
                    print(f"URL: {entry.get('uploader_url', 'Unknown')}")
                    print('-' * 50)
            print("Hi")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    get_youtube_subscriptions()