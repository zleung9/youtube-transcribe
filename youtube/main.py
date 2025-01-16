import os
import argparse
from youtube.downloader import download_video
from youtube.transcriber import transcribe_video, process, summarize
from youtube.utils import load_config


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

    # Ensure at least one of video_path or srt_path is provided
    args = parser.parse_args()

    return args


def main():
    args = parse_arguments()

    video_path, srt_path, txt_path, summary_path = None, None, None, None
    
    if args.video_id:
        # Download and transcribe video flow
        print("Downloading video...")
        video_path = download_video(args.video_id)
        print(f"Video downloaded: {video_path}")

    if args.transcribe:
        # Existing video transcription flow
        if video_path is None:
            assert args.path.endswith(".mp4"), "Please provide a valid video file in MP4 format."
            video_path = args.path
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
        summarized_path = summarize(txt_path)
        

if __name__ == "__main__":
    main()
