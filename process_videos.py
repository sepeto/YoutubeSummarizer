import os
import sys
import time
import logging
import traceback
import asyncio
from typing import Dict, List, Set
from dotenv import load_dotenv
import openai
from utils.downloader import YoutubeDownloader
from utils.audio_converter import AudioConverter
from utils.transcriber import Transcriber
from utils.summarizer import Summarizer

# Configure logging
def setup_logging():
    """Configure logging with multiple handlers for different purposes"""
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter('%(message)s')

    # Create handlers
    # Debug handler - all messages
    debug_handler = logging.FileHandler('logs/debug/debug.log', mode='w')
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(detailed_formatter)

    # Error handler - error and critical messages
    error_handler = logging.FileHandler('logs/errors/errors.log', mode='w')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)

    # Steps handler - info messages only
    steps_handler = logging.FileHandler('logs/steps/steps.log', mode='w')
    steps_handler.setLevel(logging.INFO)
    steps_handler.setFormatter(simple_formatter)

    # Console handler - info and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(detailed_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(debug_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(steps_handler)
    root_logger.addHandler(console_handler)

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Load environment variables and configure OpenAI
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Directory structure
DIRS = {
    'videos': 'videos',
    'audio': 'audio',
    'transcripts': 'transcripts',
    'summaries': 'summaries',
    'urls': 'test_urls.txt'
}

# Create directories if they don't exist
for dir_path in DIRS.values():
    if not dir_path.endswith('.txt'):
        os.makedirs(dir_path, exist_ok=True)

# Load YouTube URLs
YOUTUBE_URLS = []
try:
    with open(DIRS['urls'], 'r') as f:
        YOUTUBE_URLS = [line.strip() for line in f if line.strip()]
except Exception as e:
    logger.error(f"Failed to load URLs from {DIRS['urls']}: {str(e)}")

# Initialize components
downloader = YoutubeDownloader(DIRS['videos'])
converter = AudioConverter(DIRS['audio'])
transcriber = Transcriber(DIRS['transcripts'])
summarizer = Summarizer(DIRS['summaries'])

def get_processed_files(directory: str, extension: str) -> List[str]:
    """Get list of already processed files."""
    try:
        return [f for f in os.listdir(directory) if f.endswith(extension)]
    except Exception as e:
        logger.error(f"Failed to get processed files from {directory}: {str(e)}")
        return []

def ensure_directories():
    """Create necessary directories if they don't exist."""
    for dir_name in DIRS.values():
        if dir_name.endswith('.txt'):
            continue
        os.makedirs(dir_name, exist_ok=True)
        logger.debug(f"Directory ready: {dir_name}")

def already_exists(base_name: str, directory: str, extension: str) -> bool:
    """Check if a file with the given base name already exists."""
    target_path = os.path.join(directory, f"{base_name}{extension}")
    return os.path.exists(target_path)

async def process_videos():
    logger.info("\n=== Starting Pipeline ===\n")
    
    # Process downloads
    logger.info("Downloads:")
    success_count = 0
    failure_count = 0
    skip_count = 0
    success_files = []
    failure_files = []
    
    for url in YOUTUBE_URLS:
        try:
            filename = await downloader.download_url(url)
            if not filename:
                logger.error(f"Failed to download {url}")
                failure_count += 1
                failure_files.append(url)
            else:
                success_count += 1
                success_files.append(filename)
        except Exception as e:
            logger.error(f"Failed to download {url}: {str(e)}")
            failure_count += 1
            failure_files.append(url)
    
    logger.info(f"  + Success: {success_count}")
    logger.info(f"  - Failed: {failure_count}")
    logger.info(f"  > Skipped: {skip_count}")
    
    if success_count > 0:
        logger.info("\n  Successful files:")
        for file in success_files:
            logger.info(f"    + {os.path.basename(file)}")
            
    if failure_count > 0:
        logger.info("\n  Failed files:")
        for file in failure_files:
            logger.info(f"    - {os.path.basename(file)}")
            
    # Process conversions
    logger.info("\nConversions:")
    data = process_conversions()
    logger.info(f"  + Success: {len(data['success'])}")
    logger.info(f"  - Failed: {len(data['failed'])}")
    logger.info(f"  > Skipped: {len(data.get('skipped', []))}")
    
    if data.get('skipped'):
        logger.info("\n  Skipped files (already processed):")
        for file in data['skipped']:
            logger.info(f"    > {file}")
            
    # Process transcriptions
    logger.info("\nTranscriptions:")
    data = process_transcriptions()
    logger.info(f"  + Success: {len(data['success'])}")
    logger.info(f"  - Failed: {len(data['failed'])}")
    logger.info(f"  > Skipped: {len(data.get('skipped', []))}")
    
    if data['success']:
        logger.info("\n  Successful files:")
        for file in data['success']:
            logger.info(f"    + {os.path.basename(file)}")
            
    if data['failed']:
        logger.info("\n  Failed files:")
        for file in data['failed']:
            logger.info(f"    - {os.path.basename(file)}")
            
    # Process summaries
    logger.info("\nSummaries:")
    data = await process_summaries()
    logger.info(f"  + Success: {len(data['success'])}")
    logger.info(f"  - Failed: {len(data['failed'])}")
    logger.info(f"  > Skipped: {len(data.get('skipped', []))}")
    
    if data['success']:
        logger.info("\n  Successful files:")
        for file in data['success']:
            logger.info(f"    + {os.path.basename(file)}")
            
    logger.info("\n=== Pipeline Complete! ===\n")

def process_conversions():
    logger.info("\nConversions:")
    success_files = []
    failure_files = []
    skipped_files = []
    
    converter = AudioConverter(DIRS['audio'])
    
    for video in os.listdir(DIRS['videos']):
        try:
            if converter.convert_to_mp3(os.path.join(DIRS['videos'], video)):
                success_files.append(video)
            else:
                skipped_files.append(video)
        except Exception as e:
            logger.error(f"Failed to convert {video}: {str(e)}")
            failure_files.append(video)
            
    return {
        'success': success_files,
        'failed': failure_files,
        'skipped': skipped_files
    }

def process_transcriptions() -> Dict:
    """Transcribe audio files."""
    results = {'success': [], 'failed': [], 'skipped': []}
    transcriber = Transcriber(DIRS['transcripts'])
    
    try:
        audio_files = [f for f in os.listdir(DIRS['audio']) if f.endswith('.mp3')]
        
        for audio in audio_files:
            audio_path = os.path.join(DIRS['audio'], audio)
            
            # Check file size (25MB limit)
            if os.path.getsize(audio_path) > 25 * 1024 * 1024:
                logger.error(f"Audio file too large (>25MB): {audio}")
                results['failed'].append(audio)
                continue
                
            try:
                success, transcript_path = transcriber.transcribe_audio(audio_path)
                
                if success:
                    results['success'].append(audio)
                else:
                    results['failed'].append(audio)
                    logger.error(f"Transcription failed for {audio}")
            except Exception as e:
                logger.error(f"Failed to transcribe {audio}: {str(e)}")
                results['failed'].append(audio)
                
    except Exception as e:
        logger.error(f"Error in transcription process: {str(e)}")
        
    return results

async def process_summaries() -> Dict:
    """Generate summaries from transcripts."""
    results = {'success': [], 'failed': [], 'skipped': []}
    
    processed_files = get_processed_files(DIRS['transcripts'], '.txt')
    
    for transcript_file in processed_files:
        try:
            # Read transcription
            transcript_path = os.path.join(DIRS['transcripts'], transcript_file)
            with open(transcript_path, 'r', encoding='utf-8') as f:
                text = f.read()
                
            logger.info(f"Generating summary for {transcript_file}...")
            
            # Generate and save summary
            summary = await summarizer.generate_summary(text)
            if summary:
                results['success'].append(transcript_file)
            else:
                results['failed'].append(transcript_file)
                logger.error(f"Failed to generate summary for {transcript_file}")
                
        except Exception as e:
            logger.error(f"Failed to generate summary for {transcript_file}: {str(e)}")
            results['failed'].append(transcript_file)
            
    return results

def process_transcription(text, output_dir):
    try:
        # Create a sanitized filename from the first few words
        words = text.split()[:5]
        filename = "_".join(words) + ".txt"
        filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
        
        # Save transcription to file
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
            
        return filepath
    except Exception as e:
        logger.error(f"Failed to save transcription: {str(e)}")
        return None

if __name__ == "__main__":
    asyncio.run(process_videos()) 