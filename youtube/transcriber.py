# transcriber.py
import argparse
import os
import whisper
import torch
from openai import OpenAI
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
        result = model.transcribe(
            video_path,
            task="transcribe",
            language="zh",
            initial_prompt="请用简体中文转录以下内容。",
            fp16=True
        )
    else:
        result = model.transcribe(
            video_path,
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

    # Generate and save continuous text file
    continuous_text = remove_time_stamp(srt_path)
    with open(txt_path, "w", encoding="utf-8") as txt_file:
        txt_file.write(continuous_text)

    print(f"Transcription saved to: {srt_path}")
    print(f"Continuous text saved to: {txt_path}")

    return srt_path, txt_path


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


def process_transcription(srt_path, task="summarize", max_tokens=500):
    """
    Process the transcription using OpenAI API and save the result to a file
    Args:
        srt_path: Path to the SRT file
        task: Type of processing ("summarize", "analyze", etc.)
        max_tokens: Maximum tokens for the response
    Returns:
        str: Path to the saved output file
    """
    config = load_config()
    # Read the SRT file
    with open(srt_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Extract just the text content (removing timestamps and numbers)
    text_content = '\n'.join(
        line for line in content.split('\n')
        if not line.strip().isdigit() and '-->' not in line and line.strip()
    )

    # Initialize OpenAI client
    client = OpenAI(api_key=config['openai']['api_key'])

    # Prepare the prompt based on the task
    if task == "summarize":
        prompt = f"Please provide a concise summary of the following transcript:\n\n{text_content}"
    else:
        prompt = f"Please analyze the following transcript and {task}:\n\n{text_content}"

    # Call OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        result = response.choices[0].message.content

        # Create output file path
        output_path = os.path.splitext(srt_path)[0] + f"_{task}.txt"

        # Save the result to a file
        with open(output_path, 'w', encoding='utf-8') as output_file:
            output_file.write(result)

        return output_path
    except Exception as e:
        error_message = f"Error processing transcription: {str(e)}"
        # Save error message to file
        output_path = os.path.splitext(srt_path)[0] + f"_{task}_error.txt"
        with open(output_path, 'w', encoding='utf-8') as output_file:
            output_file.write(error_message)
        return output_path


def parse_arguments():
    parser = argparse.ArgumentParser(description="Transcribe video to SRT format.")
    parser.add_argument(
        "-t", "--video_path",
        type=str,
        required=True,
        help="Specify the path to the video file to transcribe."
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    video_path = args.video_path

    srt_path, txt_path = transcribe_video(video_path)
    print("Transcription complete!")


if __name__ == "__main__":
    main()