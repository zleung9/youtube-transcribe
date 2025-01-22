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
    srt_path = video_path.replace(".mp4", f".{language}.srt")

    # Generate and save SRT file
    srt_content = create_srt(result['segments'])
    with open(srt_path, "w", encoding="utf-8") as srt_file:
        srt_file.write(srt_content)

    print(f"Transcription saved to: {srt_path}")

    return srt_path


def process(srt_path):
    """
    Process an SRT file by extracting text lines and creating a new .txt file.
    Skips blocks with 4 lines (duplicate subtitles) and takes the last line from each valid block.

    Args:
        srt_path (str): Path to the SRT file to be processed.

    Returns:
        str: Path to the newly created text file containing extracted text.
    """
    # Read the SRT file
    with open(srt_path, 'r', encoding='utf-8') as srt_file:
        srt_text = srt_file.read()
    
    # Split into blocks by double newline
    blocks = srt_text.split('\n\n')
    
    # Extract text lines (skip blocks with 4 lines, take last line from others)
    text_lines = []
    for block in blocks:
        lines = block.strip().split('\n')
        
        # Skip blocks with 4 lines (duplicate subtitles)
        if len(lines) == 4:
            continue
            
        # Take the last line from valid blocks
        if len(lines) >= 3:  # Valid blocks have at least 3 lines
            text_lines.append(lines[-1].strip())
    
    # Join all text lines with a space
    processed_text = ' '.join(line for line in text_lines if line)
    
    # Create new filename by replacing .srt with .txt
    txt_path = srt_path.rsplit('.', 1)[0] + '.txt'
    
    # Write processed text to new file
    with open(txt_path, 'w', encoding='utf-8') as txt_file:
        txt_file.write(processed_text)
    
    print(f"Converted {srt_path} to {txt_path}")
    return txt_path
    

def summarize(
        txt_path, 
        model_name="gpt-4o", 
        provider="openai", 
        config=load_config(),
        verbose=False
    ):
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

    # Read SRT content from the file
    with open(txt_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Read system prompt from a file
    try:
        with open('youtube/prompts/summarize.md', 'r', encoding='utf-8') as prompt_file:
            system_prompt = prompt_file.read().strip()
    except FileNotFoundError:
        # Fallback to a default system prompt if file doesn't exist
        system_prompt = "You are an expert at summarizing the following article."

    user_prompt = f"""
    
    text:
    -------------------------- Begin ---------------------------------
    {content}
    -------------------------- End -----------------------------------
    
    Please generate a concise summary of the given content, and highlight key insights from the text.
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
        summary_text = response.choices[0].message.content
    except Exception:
        summary_text = f"\nError processing transcription with {provider}/{model_name}.\n"

    # Save formatted text to a file
    summary_path = txt_path.replace(".txt", ".md")
    with open(summary_path, "w", encoding="utf-8") as file:
        file.write(summary_text)
    print(f"Summary saved to file: {summary_path}")

    if verbose:
        print("\n Summary:\n")
        print(summary_text)
    
    return 

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

    video_path, srt_path, txt_path = None, None, None
    if args.transcribe:
        # Existing video transcription flow
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
