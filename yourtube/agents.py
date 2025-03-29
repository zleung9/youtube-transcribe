# Standard library imports
import os
import logging
import glob
from abc import ABC, abstractmethod
from datetime import datetime
from uuid import uuid4
import asyncio
# Third-party imports
import ffmpeg
import whisper
import litellm
from sqlalchemy import Column, String, DateTime, Boolean, UUID, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Local imports
from yourtube.utils import (
    get_download_dir,
    get_db_path,
    get_device,
    get_llm_info,
    load_config
)
from yourtube.prompts import (
    prompt_summarize,
    prompt_process_fulltext
)

logger = logging.getLogger(__name__)
Base = declarative_base()

class Video(Base):
    """Abstract base class for Video objects"""
    __tablename__ = "videos"

    id              = Column(UUID(as_uuid=True), primary_key=True, unique=True, default=uuid4)
    video_id        = Column(String(20), nullable=False)
    title           = Column(String(200), nullable=False)
    channel_id      = Column(String(20), nullable=True)
    channel         = Column(String(100), nullable=True)
    upload_date     = Column(DateTime)
    process_date    = Column(DateTime)
    language        = Column(String(10), nullable=True)  # Store primary language
    transcript      = Column(Boolean, default=False)
    fulltext        = Column(Boolean, default=False)
    summary         = Column(Boolean, default=False)
    _metadata       = {} # metadata from the 
    _default_path   = get_download_dir()

    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self):
        return f"<Video(video_id='{self.video_id}', title='{self.title}', channel='{self.channel}')>"
    
    @property
    def short_id(self):
        return self.id[:6]

    @classmethod
    def from_dict(cls, data):
        '''Create video object from JSON data'''
        return cls(**data)

    def to_dict(self):
        '''Convert video object to dictionary for selection'''
        return {
            'id': str(self.id),
            "video_id": self.video_id,
            'title': self.title,
            'channel': self.channel,
            'channel_id': self.channel_id,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'process_date': self.process_date.isoformat() if self.process_date else None,
            'language': self.language,
            'transcript': self.transcript,
            'fulltext': self.fulltext,
            'summary': self.summary
        }
    
    async def update(self, **kwargs):
        '''Update the video object with new attributes'''
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        if isinstance(self.upload_date, str):
            try:
                self.upload_date = datetime.strptime(self.upload_date, '%Y%m%d')
            except ValueError:
                self.upload_date = datetime.strptime(self.upload_date.split('T')[0], '%Y-%m-%d')
        self.process_date = datetime.now()

        path_prefix = f"{get_download_dir()}/{self.video_id}"
        self.transcript = True if os.path.exists(f"{path_prefix}.{self.language}.srt") else False
        self.fulltext = True if os.path.exists(f"{path_prefix}.{self.language}.processed.txt") else False
        self.summary = True if os.path.exists(f"{path_prefix}.{self.language}.md") else False

class Database(ABC):
    def __init__(self, db_path=None):
        self._db_lock = asyncio.Lock()  # Add class-level lock
        if db_path is None:
            self.db_path = get_db_path()
        else:
            self.db_path = db_path

    async def add_video(self, video):
        return await self._add_video(video)

    async def delete_video(self, **kwargs):
        return await self._delete_video(**kwargs)
    
    async def refresh_database(self):
        raise NotImplementedError
    
    async def get_videos(self, **kwargs):
        return  await self._get_videos(**kwargs)

    
    async def update_video(self, video: Video):
        """Update an existing video in the database without deleting/re-adding."""
        async with self._db_lock:
            try:
                # Get existing video
                existing_videos = await self.get_videos(video_id=video.video_id)
                
                if not existing_videos:
                    return await self.add_video(video)
                
                # Store the ID of the existing video
                existing_video = existing_videos[0]
                # Update attributes instead of deleting/re-adding
                for attr in ['transcript', 'fulltext', 'summary', 'process_date', 'language']:
                    if hasattr(video, attr):
                        setattr(existing_video, attr, getattr(video, attr))
                
                self.session.commit()
                return True

            except Exception as e:
                self.session.rollback()
                raise Exception(f"Error updating video: {str(e)}")
    

    @abstractmethod
    async def _add_video(self, video: Video):
        """Add a new video to the database."""
        raise NotImplementedError
    
    @abstractmethod
    async def _delete_video(self, **kwargs):
        """Delete a video from the database."""
        raise NotImplementedError
    
    @abstractmethod
    async def _get_videos(self, **kwargs):
        """Get a video from the database."""
        raise NotImplementedError


class SqliteDB(Database):
    def __init__(self, db_path='videos.db'):
        super().__init__(db_path)
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        Base.metadata.create_all(self.engine)  # Create tables if they don't exist
        self.Session = sessionmaker(bind=self.engine)
        self.session = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = self.Session()
        return self


    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            if exc_type is not None:
                # If there was an exception, rollback
                self.session.rollback()
            else:
                # If no exception, commit
                self.session.commit()
            self.session.close()
            self.session = None


    async def _add_video(self, video: Video):
        """Add a new video to the database."""
        try:
            self.session.add(video)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Error adding video: {str(e)}")


    async def _delete_video(self, **kwargs):
        """Delete a video from the database."""
        try:
            video = self.get_videos(**kwargs)[0]
            if video:
                self.session.delete(video) # remove from database
                self.session.commit() 
                for file in glob.glob(f"{get_download_dir()}/{video.video_id}.*", recursive=True):
                    print(file)
                    try:
                        os.remove(file)
                    except OSError as e:
                        print(f"Error deleting file: {file}")
                print(f"Successfully deleted videos filtered by: {kwargs}")
                return True
            else:
                print(f"No videos found filtered by: {kwargs}")
                return False
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Error deleting video: {str(e)}")

    async def _get_videos(self, **kwargs):
        '''If video_id exists in database, return video, other wise None
        '''
        try:
            video = self.session.query(Video).filter_by(**kwargs).all()
            return video
        except Exception as e:
            self.session.rollback()
            raise IndexError(f"Something went wrong when trying to get video: {e}")


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
        ffmpeg.input(audio_path).output(
            output_path, 
            ar='16000',    # Sample rate
            ac=1,          # Mono audio
            acodec='pcm_s16le'
        ).run(overwrite_output=True, quiet=True)
        print(f"Audio preprocessed to: {output_path}")
        return output_path
    except Exception as e:
        print(f"Error processing audio: {e}")
        return None



class AsyncAgent(ABC):
    def __init__(self, config: dict):
        self._config = config
        self._running = False
        self._poll_interval = config.get('poll_interval', 30)  # seconds
        self.working_dir = get_download_dir()
        self._video = None
        self._video_path = ""
        self._srt_path = ""
        self._txt_path = ""
        self._processed_txt_path = ""
        self._md_path = ""
        self._language = "zh" # default language is Chinese
        self._db_lock = asyncio.Lock()  # Add a database lock
        self.name = None
    
    async def start(self):
        """Start the agent's monitoring loop"""
        self._running = True
        print(f"Starting {self.name}...")
        while self._running:
            try:
                await self.process_batch()
                await asyncio.sleep(self._poll_interval)
            except Exception as e:
                logger.error(f"Error in {self.__class__.__name__}: {e}")
                await asyncio.sleep(self._poll_interval)
    

    async def stop(self):
        """Stop the agent"""
        self._running = False

    
    @abstractmethod
    async def process_batch(self):
        """Process a batch of items"""
        pass

    @abstractmethod
    async def _process_single_video(self, video, db):
        pass

    async def load_video(self, video: Video):
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
        self._processed_txt_path = self._txt_path.replace(".txt", ".processed.txt")
        self._md_path = self._video_path.replace(".mp4", f".{self._language}.md")

    async def update_video_safe(self, db, video):
        """Thread-safe video update"""
        async with self._db_lock:
            await db.update_video(video)


class AsyncTranscriber(AsyncAgent):
    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "transcriber"
        self.model = None
    

    async def process_batch(self):
        """Process videos that need transcription"""
        async with SqliteDB(db_path=get_db_path(test=True)) as db:
            videos = await db.get_videos(transcript=False)
            if not videos:
                return
            # Load model if not loaded
            if not self.model:
                await self._load_model()
            
            for video in videos:
                await self._process_single_video(video, db)
            # Release model if no more videos to process
            self._release_model()
    
    async def _process_single_video(self, video, db):
        try:
            print(f"Transcribing video {video.video_id}")
            await self._transcribe(video)
            video.transcript = True
            await self.update_video_safe(db, video)  # Use safe update
            print(f"Finished transcribing video {video.video_id}")
        except Exception as e:
            logger.error(f"Failed to transcribe video {video.video_id}: {e}")


    async def _load_model(self, model_size: str="base"):
        """
        Load the Whisper model with GPU acceleration if available.

        Args:
            model_size (str, optional): Name of the Whisper model to load. Defaults to "base".
        """
        # Try to use MPS/GPU first, fallback to CPU if there are issues
        try:
            self.device = get_device()
            self.model = whisper.load_model(model_size).to(self.device)
        except (NotImplementedError, RuntimeError):
            print("GPU acceleration failed, falling back to CPU...")
            self.device = "cpu"
            self.model = whisper.load_model(model_size).to(self.device)


    async def _transcribe(self, video: Video):
        """
        Transcribe video audio to text and save as SRT file.
        Includes language detection and optimized transcription settings.

        Args:
            video (Video): Video object to transcribe

        Returns:
            int: 0 on success, 1 on failure
        """
        assert self.model, "Model not loaded."
        
        await self.load_video(video)
        print("Detecting language...", end="\r", flush=True)
        
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
        print("Transcribing...", end="\r", flush=True)
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
        
        except Exception as e:
            self._srt_path = ""
            print(f"Error transcribing video: {e}")

    def _release_model(self):
        """
        Release the loaded Whisper model from memory.
        """
        try:
            del self.model
            self.model = None
            print("Model memory released")
        except Exception as e:
            print(f"Error releasing model: {e}")


class AsyncTextProcessor(AsyncAgent):
    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "text_processor"    

    async def process_batch(self):
        """Process videos that need summarization"""
        async with SqliteDB(db_path=get_db_path(test=True)) as db:
            videos = await db.get_videos(transcript=True, fulltext=False)
            # Create tasks for all videos
            tasks = []
            for video in videos:
                task = asyncio.create_task(self._process_single_video(video, db))
                tasks.append(task)
            
            # Process all videos in parallel
            await asyncio.gather(*tasks)


    async def _process_single_video(self, video, db):
        try:
            print(f"Processing text for video {video.video_id}")
            content = await self._extract_fulltext(video)
            if isinstance(content, Video): # video is returned if srt file is not found
                await self.update_video_safe(db, video)
                return
            content = await self._process_fulltext(content)

            await self.update_video_safe(db, video)
            print(f"Finished processing text for video {video.video_id}")
        except Exception as e:
            logger.error(f"Failed to process text for video {video.video_id}: {e}")


    async def _extract_fulltext(self, video: Video):
        """
        Process SRT file to extract clean text content.
        Removes timestamps and formatting, combining all text into a single file.

        Args:
            video (Video): Video object containing file information

        Returns:
            int: 0 on success, 1 on failure
        """
        # Read the SRT file
        try:
            with open(self._srt_path, 'r', encoding='utf-8') as srt_file:
                srt_text = srt_file.read()
        except FileNotFoundError:
            print(f"SRT file not found: {self._srt_path}")
            video.transcript = False
            return video

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
        
        print(f"Converted srt to txt: {self._txt_path}")
        return processed_text
    

    async def _process_fulltext(self, content: str, chunk_size: int=2000, overlap: int=200):
        """
        Process the fulltext of the video. The purpose is to reorganize the text into a more readable format. It does the following:
        1. Read the fulltext from the txt file and divide it into chunks of 1000 tokens/words each with an overlap.
        2. Iterate over chunks:
            For each chunk, feed to `prompt_process_fulltext` function to create a prompt for the LLM, and get the output of from LLM.
        4. Create a new txt file and write the output of the LLM to it and append the output of LLM to the file for each iteration.
        
        Args:
            video (Video): Video object containing file information
            chunk_size (int, optional): Size of each chunk in tokens/words. Defaults to 1000.
            overlap (int, optional): Number of tokens/words to overlap between chunks. Defaults to 200.
            
        Returns:
            str: Processed content
        """
        
        # Get LLM information from config
        llm_provider, llm_name, api_key, max_tokens, temperature = get_llm_info("process_fulltext")
        words = list(content) if self._language == "zh" else content.split() # For Chinese, we split by characters since each character is a token
        
        # Create chunks with overlap
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            # Make sure we don't go beyond the end of the list
            end_idx = min(i + chunk_size, len(words))
            chunk = words[i:end_idx]
            chunks.append(''.join(chunk) if self._language == "zh" else ' '.join(chunk))
            # If we've reached the end, break
            if end_idx == len(words):
                break
        
        # Process each chunk with LLM
        processed_content = ""
        starting_text = ""  # Initial starting text is empty
        
        for i, chunk in enumerate(chunks):
            print(f"Processing text: {i+1}/{len(chunks)}", end="\r", flush=True)
            # Create prompt for LLM
            try:
                response = litellm.completion(
                    messages=[{
                        "role": "user", 
                        "content": prompt_process_fulltext(chunk, starting_text, self._language)
                    }],
                    model=f"{llm_provider}/{llm_name}",
                    api_key=api_key,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            except Exception as e:
                print(f"LLM error processing chunk {i+1}: {e}")
                raise
            chunk_result = response.choices[0].message.content
            
            # Extract the last paragraph for use as starting text for next chunk
            last_paragraph = ""
            content_to_append = chunk_result
            whitespace = '\n\n'
            paragraphs = chunk_result.split(whitespace)
            if len(paragraphs) > 1:
                # If we have multiple paragraphs, use the last one as starting text
                # and append all but the last paragraph to processed_content
                last_paragraph = paragraphs[-1]
                content_to_append = whitespace.join(paragraphs[:-1])
            else:
                # If no double-newline paragraph breaks, try splitting by single newlines
                whitespace = '\n'   
                paragraphs = chunk_result.split(whitespace)
                if len(paragraphs) > 1:
                    last_paragraph = paragraphs[-1]
                    content_to_append = whitespace.join(paragraphs[:-1])
                else:
                    # If no paragraph breaks at all, use the entire chunk as the last paragraph
                    last_paragraph = chunk_result
                    content_to_append = ""
            
            # Append the content (without the last paragraph) to the processed content
            processed_content += whitespace + content_to_append
            starting_text = last_paragraph

        processed_content += whitespace + last_paragraph # Append the last paragraph to the processed content
        # Create a new file for the processed content
        processed_txt_path = self._txt_path.replace(".txt", ".processed.txt")
        with open(processed_txt_path, 'w', encoding='utf-8') as file:
            # Strip leading newlines before writing to file
            file.write(processed_content.lstrip('\n'))
        
        print(f"Processed fulltext saved to: {processed_txt_path}")
        
        # Update the txt path to the processed file
        self._txt_path = processed_txt_path
        return processed_content
    

class AsyncSummarizer(AsyncAgent):
    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "summarizer"

    async def process_batch(self):
        """Process videos that need summarization"""
        async with SqliteDB(db_path=get_db_path(test=True)) as db:
            videos = await db.get_videos(fulltext=True, summary=False)
            # Create tasks for all videos
            tasks = []
            for video in videos:
                task = asyncio.create_task(self._process_single_video(video, db))
                tasks.append(task)
            
            # Process all videos in parallel
            await asyncio.gather(*tasks)

    async def _process_single_video(self, video, db):
        try:
            print(f"Summarizing video {video.video_id}")
            await self._summarize(video)
            video.summary = True
            await self.update_video_safe(db, video)
            print(f"Finished summarizing video {video.video_id}")
        except Exception as e:
            logger.error(f"Failed to summarize video {video.video_id}: {e}")


    async def _summarize(self, video: Video, verbose=False):
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
        # Use the processed text file if it exists, otherwise use the original text file
        await self.load_video(video)
        txt_path = self._processed_txt_path if os.path.exists(self._processed_txt_path) else self._txt_path
        
        llm_provider, llm_name, api_key, max_tokens, temperature = get_llm_info("summarize")

        # Read content from the file
        try:
            with open(txt_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except FileNotFoundError:
            self.extract_fulltext(video)
            with open(txt_path, 'r', encoding='utf-8') as file:
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


class WorkflowManager:
    def __init__(self, config: dict):
        self.config = config
        self.agents = []
        self._setup_agents()
    
    def _setup_agents(self):
        """Initialize all agents"""
        self.agents.extend([
            AsyncTranscriber(self.config),
            AsyncTextProcessor(self.config),
            AsyncSummarizer(self.config)
        ])
        
        # Easy to add more agents here
    
    async def start(self):
        """Start all agents"""
        tasks = [
            asyncio.create_task(agent.start())
            for agent in self.agents
        ]
        await asyncio.gather(*tasks)
    
    async def stop(self):
        """Stop all agents"""
        await asyncio.gather(*[agent.stop() for agent in self.agents])


async def main():
    config = load_config()
    
    # Scan the database to see if transcript, fulltext, and summary files exist
    async with SqliteDB(db_path=get_db_path(test=True)) as db:
        for video in await db.get_videos():
            await video.update()
            await db.update_video(video)
    
    workflow = WorkflowManager(config)
    
    try:
        await workflow.start()
    except KeyboardInterrupt:
        await workflow.stop()

if __name__ == "__main__":
    asyncio.run(main())