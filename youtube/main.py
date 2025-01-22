import os
import argparse
from youtube.utils import load_config
from youtube.downloader import download_video
from youtube.transcriber import transcribe_video, process, summarize
from app.db_models import Session, Video
from app.scanner import scan_downloads_folder


def parse_arguments():
    parser = argparse.ArgumentParser(description="Transcribe video to SRT format or process an existing SRT file.")
    parser.add_argument(
        "-y", '--video_id', 
        type=str, 
        help="YouTube video ID to download"
    )
    parser.add_argument(
        "-t", "--transcribe",
        action="store_true",
        default=False,
        help="Whether to transcribe a video file."
    )
    parser.add_argument(
        "-p", "--process",
        action="store_true",
        default=False,
        help="Whether to process an existing SRT file."
    )
    parser.add_argument(
        "-s", "--summmarize",
        action="store_true",
        default=False,
        help="Whether to summarize the transcription."
    )
    parser.add_argument(
        "-f", "--path",
        type=str,
        help="Specify the path to an existing video to transcribe or an SRT file to process.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Display the summary in the terminal after processing."
    )
    parser.add_argument(
        "-d", "--database",
        action="store_true",
        default=False,
        help="Whether to store the results in the database."
    )

    # Ensure at least one of video_path or srt_path is provided
    args = parser.parse_args()

    return args


def process_video_pipeline(video_id):
    """Process a video through the entire pipeline."""
    config = load_config()
    session = Session()
    
    try:
        # Check if video already exists
        existing_video = session.query(Video).filter_by(video_id=video_id).first()
        if existing_video:
            raise Exception(f"Video {video_id} already processed")

        # Download and get metadata
        print("Downloading video...")
        metadata = download_video(video_id, config=config)
        video_path = metadata['video_path']
        srt_path = metadata['srt_path']

        # Transcribe if needed
        if not os.path.exists(srt_path):
            print("Transcribing video...")
            srt_path = transcribe_video(video_path)

        # Process transcript
        print("Processing transcript...")
        txt_path = process(srt_path)

        # Generate summary
        print("Generating summary...")
        summarize(txt_path, verbose=False, config=config)

        # Update database
        scan_downloads_folder(
            downloads_path=config['paths']['downloads'],
            video_ids=[video_id]
        )

        return True
    except Exception as e:
        raise Exception(f"Error processing video: {str(e)}")
    finally:
        session.close()


def main():
    config = load_config()
    args = parse_arguments()
    session = Session()
    video_path, srt_path, txt_path = None, None, None
    
    if args.video_id:
        # Check if video already exists in database
        existing_video = session.query(Video).filter_by(video_id=args.video_id).first()
        if existing_video:
            print(f"Video {args.video_id} already processed")
            return
        # Download and transcribe video flow
        print("Downloading video...")
        metadata = download_video(args.video_id, config=config)
        video_path = metadata['video_path']
        srt_path = metadata['srt_path']
    
    if args.transcribe:
        # Existing video transcription flow
        if video_path is None:
            assert args.path.endswith(".mp4"), "Please provide a valid video file in MP4 format."
            video_path = args.path
        # Transcribe video if srt is not downloaded.
        if not srt_path:        
            print(f"Transcribing video")
            srt_path = transcribe_video(video_path)
    
    if args.process:
        if srt_path is None:
            assert args.path is not None, "No SRT file to process."
            srt_path = args.path
        # Existing SRT file processing flow
        print(f"Processing SRT file.")
        txt_path = process(srt_path)

    if args.summmarize:
        if txt_path is None:
            assert args.path is not None, "No transcription file to summarize."
            txt_path = args.path
        print(f"Summarizing transcription.")
        summarize(txt_path, verbose=args.verbose, config=config)
        
    # Create new video entry
    if args.database:
        scan_downloads_folder(
            downloads_path=config['paths']['downloads'],
            video_ids=[args.video_id]
        )


if __name__ == "__main__":
    main()
