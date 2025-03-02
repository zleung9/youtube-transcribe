# transcriber.py
import os
import whisper
import litellm
import ffmpeg
from yourtube import Video
from yourtube.utils import get_device, get_download_dir, get_llm_info
from yourtube.prompts import prompt_summarize


def format_timestamp(seconds):
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,mmm).

    Args:
        seconds (float): Time in seconds

    Returns:
        str: Formatted timestamp string in format "HH:MM:SS,mmm"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def create_srt(segments):
    """
    Convert transcription segments to SRT format.

    Args:
        segments (list): List of dictionaries containing segment information
                        Each segment should have 'start', 'end', and 'text' keys

    Returns:
        str: Complete SRT formatted string with all segments
    """
    srt_content = []
    for i, segment in enumerate(segments, start=1):
        start_time = format_timestamp(segment['start'])
        end_time = format_timestamp(segment['end'])
        text = segment['text'].strip()

        srt_entry = f"{i}\n{start_time} --> {end_time}\n{text}\n"
        srt_content.append(srt_entry)

    return "\n".join(srt_content)


def preprocess_audio(audio_path):
    """
    Pre-process audio file for better transcription quality.
    Converts audio to 16kHz mono WAV format.

    Args:
        audio_path (str): Path to the input audio/video file

    Returns:
        str: Path to the processed audio file, or None if processing fails
    """
    try:
        # Convert to 16kHz mono WAV
        output_path = audio_path.replace('.mp4', '.wav')
        ffmpeg.input(audio_path).output(output_path, 
                                         ar='16000',    # Sample rate
                                         ac=1,          # Mono audio
                                         acodec='pcm_s16le').run(overwrite_output=True)
        print(f"Audio preprocessed to: {output_path}")
        return output_path
    except Exception as e:
        print(f"Error processing audio: {e}")
        return None
        
class Transcriber:
    def __init__(self, video: Video|None=None, model_name="base"):
        
        self.working_dir = get_download_dir()
        self.model_name = model_name
        self.device = None
        self.model = None
        self._video_path = ""
        self._srt_path = ""
        self._txt_path = ""
        self._md_path = ""
        self._video_id = None
        self._language = "zh" # default language is Chinese
        if video:
            self.load_video(video)
        if model_name:
            self.load_model(model_name)

    @property
    def metadata(self):
        return {
            "summary": True if self._md_path and os.path.exists(self._md_path) else False,
            "transcription": True if self._srt_path and os.path.exists(self._srt_path) else False,
            "fulltext": True if self._txt_path and os.path.exists(self._txt_path) else False,
            "language": self._language
        }

    def load_model(self, model_name: str="base"):
        """
        Load the Whisper model with GPU acceleration if available.

        Args:
            model_name (str, optional): Name of the Whisper model to load. Defaults to "base".
        """
        # Try to use MPS/GPU first, fallback to CPU if there are issues
        try:
            self.device = get_device()
            self.model = whisper.load_model(model_name).to(self.device)
        except (NotImplementedError, RuntimeError):
            print("GPU acceleration failed, falling back to CPU...")
            self.device = "cpu"
            self.model = whisper.load_model(model_name).to(self.device)
    

    def load_video(self, video: Video):
        """
        Load video into the transcriber and set up file paths.

        Args:
            video (Video): Video object containing video information
        """
        self._video = video
        self._language = video.language

        self._video_path = os.path.join(self.working_dir, f"{video.video_id}.mp4")
        self._srt_path = self._video_path.replace(".mp4", f".{self._language}.srt")
        self._txt_path = self._video_path.replace(".mp4", f".{self._language}.txt")
        self._md_path = self._video_path.replace(".mp4", f".{self._language}.md")


    def transcribe(self, video: Video):
        """
        Transcribe video audio to text and save as SRT file.
        Includes language detection and optimized transcription settings.

        Args:
            video (Video): Video object to transcribe

        Returns:
            int: 0 on success, 1 on failure
        """
        if not self.model:
            self.load_model()
        
        self.load_video(video)
        print("Detecting language...")
        
        # If audio processing fails, return an error
        processed_audio_path = preprocess_audio(self._video_path)
        if processed_audio_path is None:
            print("Audio preprocessing failed, using video directly.")
            processed_audio_path = self._video_path
        
        # Use the model initialized in __init__
        model = self.model

        # First detect the language
        audio = whisper.load_audio(processed_audio_path)
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(model.device)
        _, probs = model.detect_language(mel)
        language = max(probs, key=probs.get)
        print(f"Detected language: {language}")

        try:
            result = model.transcribe(
                processed_audio_path,
                task="transcribe",
                language=language,
                initial_prompt="以下是一段中文视频内容的转录。请使用简体中文准确转录，保持原有的语气和表达方式。" if language == "zh" else None,
                fp16=self.device != "cpu", # Use half-precision floating point for faster processing
                beam_size=1, # Increase beam search width (default is 1)
                best_of=1, # Generate multiple samples and select best (default is 1)
                temperature=0.0, # Lower temperature for more deterministic output
                condition_on_previous_text=True, # Use previous text as condition
                compression_ratio_threshold=2, # Prevent empty segments
                no_speech_threshold=0.6, # Prevent empty segments
                word_timestamps=False # Generate word-level timestamps
            )
            srt_content = create_srt(result['segments'])
            with open(self._srt_path, "w", encoding="utf-8") as srt_file:
                srt_file.write(srt_content)
            print(f"Transcription saved to: {self._srt_path}")
            
            # delete the video file after transcribing
            for suffix in ['mp4', 'wav']:
                try: 
                    os.remove(os.path.join(self.working_dir, f'{video.video_id}.{suffix}'))
                except FileNotFoundError:
                    continue
            
            return srt_content
        
        except Exception as e:
            self._srt_path = ""
            print(f"Error transcribing video: {e}")
            return None

    def release_model(self):
        """
        Release the loaded Whisper model from memory.
        """
        try:
            del self.model
            self.model = None
            print("Model memory released")
        except Exception as e:
            print(f"Error releasing model: {e}")

    def process(self, video: Video):
        """
        Process SRT file to extract clean text content.
        Removes timestamps and formatting, combining all text into a single file.

        Args:
            video (Video): Video object containing file information

        Returns:
            int: 0 on success, 1 on failure
        """
        self.load_video(video)
        # Read the SRT file
        try:
            with open(self._srt_path, 'r', encoding='utf-8') as srt_file:
                srt_text = srt_file.read()
        except FileNotFoundError:
            print(f"SRT file not found: {self._srt_path}")
            self.transcribe(video)
            with open(self._srt_path, 'r', encoding='utf-8') as srt_file:
                srt_text = srt_file.read()

        # Split into blocks by double newline
        blocks = srt_text.split('\n\n')
        
        # Extract text lines (skip blocks with 4 lines, take last line from others)
        text_lines = []
        for block in blocks:
            lines = block.strip().split('\n')
                
            # Take the last line from valid blocks
            if len(lines) >= 3:  # Valid blocks have at least 3 lines
                text_lines.append(lines[-1].strip())
        
        # Join all text lines with a space
        processed_text = ' '.join(line for line in text_lines if line)
        
        # Write processed text to new file
        with open(self._txt_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(processed_text)
        
        print(f"Converted {self._srt_path} to {self._txt_path}")
        return processed_text
    

    def summarize(self, video: Video, verbose=False):
        """
        Generate a summary of the transcribed content using LLM.

        Args:
            video (Video): Video object containing transcription.
            verbose (bool, optional): Whether to print the summary. Defaults to False.

        Returns:
            int: 0 on success, 1 on failure

        Notes:
            - Reads from the processed text file (.txt)
            - Uses LiteLLM to generate summary
            - Saves summary in markdown format (.md)
        """
        self.load_video(video)
        llm_provider, llm_name, api_key, max_tokens, temperature = get_llm_info("summarizer")

        # Read SRT content from the file
        try:
            with open(self._txt_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except FileNotFoundError:
            self.process(video)
            with open(self._txt_path, 'r', encoding='utf-8') as file:
                content = file.read()
        try:
            # Use LiteLLM to get response from the specified provider
            response = litellm.completion(
                messages=[{"role": "user", "content": prompt_summarize(content)}],
                model=f"{llm_provider}/{llm_name}",
                api_key=api_key,
                max_tokens=max_tokens,
                temperature=temperature
            )
            summary_text = response.choices[0].message.content
        except Exception as e:
            print(f"\nError processing transcription with {e}.\n")
        
        # Save formatted text to a file
        summary_path = self._txt_path.replace(".txt", ".md")
        with open(summary_path, "w", encoding="utf-8") as file:
            file.write(summary_text)
        print(f"Summary saved to file: {summary_path}")

        if verbose:
            print("\n Summary:\n")
            print(summary_text)
        
        return summary_text