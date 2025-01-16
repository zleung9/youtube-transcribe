# transcriber.py
import argparse
import os
import whisper
import litellm
import torch
from youtube.utils import load_config


def get_device():
    """Get the device for running Whisper"""
    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    if device in ["cuda", "mps"]:
        print(f"Device detected: {device}")
    return device


def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def create_srt(segments):
    """Convert transcription segments to SRT format"""
    srt_content = []
    for i, segment in enumerate(segments, start=1):
        start_time = format_timestamp(segment['start'])
        end_time = format_timestamp(segment['end'])
        text = segment['text'].strip()

        srt_entry = f"{i}\n{start_time} --> {end_time}\n{text}\n"
        srt_content.append(srt_entry)

    return "\n".join(srt_content)


def transcribe_video(video_path):
    """Transcribe video and save as both SRT and continuous text files"""
    print("Loading Whisper model...")
    # Enable CoreML for Apple Silicon/Metal GPU acceleration
    device = get_device()
    try:
        model = whisper.load_model("base").to(device)
    except NotImplementedError:
        device = "cpu"
        model = whisper.load_model("base").to(device)
    print(f"Running Whisper on {device}")
    print("Detecting language...")
    # First detect the language
    audio = whisper.load_audio(video_path)
    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio).to(model.device)
    _, probs = model.detect_language(mel)
    detected_lang = max(probs, key=probs.get)

    print(f"Detected language: {detected_lang}")

    # If Chinese is detected, force Simplified Chinese output
    if detected_lang == "zh":
        language = "zh"
        initial_prompt = "请用简体中文转录以下内容。"
    else:
        language = "en"
        initial_prompt = None

    result = model.transcribe(
        video_path,
        task="transcribe",
        language=language,
        initial_prompt=initial_prompt,
        fp16=True
    )

    del model

    # Create file paths
    base_path = os.path.splitext(video_path)[0]
    srt_path = base_path + ".srt"
    txt_path = base_path + ".txt"

    # Generate and save SRT file
    srt_content = create_srt(result['segments'])
    with open(srt_path, "w", encoding="utf-8") as srt_file:
        srt_file.write(srt_content)

    print(f"Transcription saved to: {srt_path}")

    return srt_path


def remove_time_stamp(srt_path):
    """
    Convert an SRT file into continuous text by removing timestamps and numbers.
    Args:
        srt_path: Path to the SRT file.

    Returns:
        str: Continuous text extracted from the SRT file.
    """
    with open(srt_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Extract just the text content (removing timestamps and numbers)
    continuous_text = '\n'.join(
        line.strip() for line in content.split('\n')
        if not line.strip().isdigit() and '-->' not in line and line.strip()
    )

    return continuous_text


def process_transcription(srt_path, model_name="gpt-4o", provider="openai", chunk_size=80):
    """
    Process the transcription text file by converting it into a well-formatted article
    using a specific language model through LiteLLM.

    Args:
        srt_path (str): Path to the input SRT file
        model_name (str): Name of the LLM model to use
        provider (str): LLM provider (e.g., "openai", "anthropic")
        chunk_size (int): Maximum number of time stamps per chunk in the srt file.

    Returns:
        str: Path to the output formatted article file
    """
    # Load configuration
    config = load_config()

    # Read SRT content from the file
    with open(srt_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Read system prompt from a file
    try:
        with open('youtube/prompts/process_transcription.md', 'r', encoding='utf-8') as prompt_file:
            system_prompt = prompt_file.read().strip()
    except FileNotFoundError:
        # Fallback to a default system prompt if file doesn't exist
        system_prompt = "You are an expert at converting transcribed text into a well-formatted, flowing article."

    # Split SRT content into blocks (each block separated by empty lines)
    srt_blocks = content.strip().split('\n\n')

    processed_content = ""
    for i in range(0, len(srt_blocks), chunk_size):
        chunk = srt_blocks[i: i + chunk_size]
        content = '\n\n'.join(chunk)

        user_prompt = f"""
        Transcription Text:
        {content}
        
        Please provide the reformatted text as a complete, flowing article.
        """

        try:
            # Use LiteLLM to get response from the specified provider
            response = litellm.completion(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                api_key=config.get(provider, {}).get("api_key"),
                max_tokens=4096,
                temperature=0.7
            )
            formatted_text = response.choices[0].message.content
        except Exception:
            formatted_text = f"\nError processing transcription with {provider}/{model_name}.\n"

        processed_content += formatted_text + "\n\n"

        # Save formatted text to a file
        txt_path = os.path.splitext(srt_path)[0] + ".txt"
        with open(txt_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(processed_content)
        print(f"SRT file processed. Formatted text saved to: {txt_path}")

    return txt_path


def parse_arguments():
    parser = argparse.ArgumentParser(description="Transcribe video to SRT format or process an existing SRT file.")
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
    assert args.path is not None, "Please provide a path to a video file or an SRT file."

    return args


def main():
    args = parse_arguments()

    srt_path, txt_path = None, None
    if args.transcribe:
        # Existing video transcription flow
        assert args.path.endswith(".mp4"), "Please provide a valid video file in MP4 format."
        srt_path = transcribe_video(args.path)
        print("Video transcription complete!")    
    
    if args.process:
        if srt_path is None:
            srt_path = args.path
            assert srt_path is not None, "No SRT file to process."
        # Existing SRT file processing flow
        txt_path = process_transcription(srt_path)


if __name__ == "__main__":
    main()
