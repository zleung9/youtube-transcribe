import os
import argparse
from yourtube import Video, YoutubeVideo, SqliteDB, Transcriber
from yourtube.utils import extract_youtube_id


def main():
    parser = argparse.ArgumentParser(description="Transcribe video to SRT format or process an existing SRT file.")
    parser.add_argument("-y", '--youtube_url', type=str, help="YouTube video url to download")
    parser.add_argument("-t", "--transcribe", action="store_true", default=False, help="Whether to transcribe a video file.")
    parser.add_argument("-p", "--process", action="store_true", default=False, help="Whether to process an existing SRT file.")
    parser.add_argument("-s", "--summarize", action="store_true", default=False, help="Whether to summarize the transcription.")
    parser.add_argument("-f", "--path", type=str, help="Specify the path to an existing video to transcribe or an SRT file to process.")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Display the summary in the terminal after processing.")

    args=parser.parse_args()
    db = SqliteDB()
    # Check if video already 
    video_id = extract_youtube_id(args.youtube_url)
    video = db.get_video(video_id=video_id)
    if video:
        print(f"Video {video_id} already processed")
        return

    # Download and transcribe video flow
    video = YoutubeVideo()
    video.get(video_id, download_video=True, download_json=True)
    
    transcriber = Transcriber(model_name="base")

    if args.transcribe:
        print(f"Transcribing video")
        _ = transcriber.transcribe(video)
    
    if args.process:
        print(f"Processing SRT file.")
        _ = transcriber.process(video)

    if args.summarize:
        print(f"Summarizing transcription.")
        _ = transcriber.summarize(video, title="anthropic-claude-3.5-sonnet")
    
    # Add to database
    video.update(**transcriber.metadata) 
    db.add_video(video)
    print(f"Successfully downloaded video: {video.title}")
    
    transcriber.release_model()
 

if __name__ == "__main__":
    main()   
