import os
import asyncio
import logging
from datetime import datetime
from typing import List, Optional
import openai
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
import yaml

# Cargar variables de entorno
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MediaProcessor:
    def __init__(self):
        self.config = self._load_config()
        self.downloads_dir = "Descargas"
        self.transcripts_dir = "Transcripciones"
        self.summaries_dir = "Resumenes"
        self._ensure_directories()
    
    def _load_config(self) -> dict:
        """Carga la configuración desde config.yaml"""
        try:
            with open("config.yaml", 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return {
                'download': {
                    'type': 'video',
                    'video_quality': 'highest',
                    'audio_format': 'mp3',
                    'audio_quality': 320,
                    'output_dir': 'Descargas'
                }
            }
    
    def _ensure_directories(self):
        """Asegura que existan los directorios necesarios"""
        for directory in [self.downloads_dir, self.transcripts_dir, self.summaries_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def _extract_audio(self, video_path: str) -> str:
        """Extrae el audio de un video y lo guarda como MP3"""
        try:
            video = VideoFileClip(video_path)
            audio_path = os.path.splitext(video_path)[0] + '.mp3'
            video.audio.write_audiofile(audio_path)
            video.close()
            return audio_path
        except Exception as e:
            logger.error(f"Error extracting audio from {video_path}: {str(e)}")
            return None
    
    async def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """Transcribe un archivo de audio usando OpenAI Whisper"""
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = await openai.Audio.atranscribe(
                    "whisper-1",
                    audio_file
                )
            
            # Guardar transcripción
            transcript_path = os.path.join(
                self.transcripts_dir,
                os.path.splitext(os.path.basename(audio_path))[0] + '_transcript.txt'
            )
            
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(transcript['text'])
            
            logger.info(f"Transcription saved to {transcript_path}")
            return transcript_path
            
        except Exception as e:
            logger.error(f"Error transcribing {audio_path}: {str(e)}")
            return None
    
    async def summarize_transcript(self, transcript_path: str) -> Optional[str]:
        """Resume una transcripción usando OpenAI GPT"""
        try:
            # Leer transcripción
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
            
            # Leer prompt
            with open('prompt.txt', 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            
            # Crear prompt completo
            prompt = prompt_template.format(transcript=transcript_text)
            
            # Generar resumen
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates concise summaries."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            summary = response.choices[0].message.content
            
            # Guardar resumen
            summary_path = os.path.join(
                self.summaries_dir,
                os.path.splitext(os.path.basename(transcript_path))[0] + '_summary.txt'
            )
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            logger.info(f"Summary saved to {summary_path}")
            return summary_path
            
        except Exception as e:
            logger.error(f"Error summarizing {transcript_path}: {str(e)}")
            return None
    
    async def process_video(self, video_path: str):
        """Procesa un video: extrae audio, transcribe y resume"""
        logger.info(f"Processing video: {video_path}")
        
        # Extraer audio
        audio_path = self._extract_audio(video_path)
        if not audio_path:
            return
        
        # Transcribir
        transcript_path = await self.transcribe_audio(audio_path)
        if not transcript_path:
            return
        
        # Resumir
        summary_path = await self.summarize_transcript(transcript_path)
        if not summary_path:
            return
        
        logger.info(f"Completed processing {video_path}")
    
    async def process_directory(self):
        """Procesa todos los videos en el directorio de descargas"""
        video_files = [
            os.path.join(self.downloads_dir, f) 
            for f in os.listdir(self.downloads_dir) 
            if f.endswith(('.mp4', '.webm', '.mkv'))
        ]
        
        if not video_files:
            logger.warning("No video files found in downloads directory")
            return
        
        logger.info(f"Found {len(video_files)} video files to process")
        
        # Procesar videos en paralelo
        tasks = [self.process_video(video) for video in video_files]
        await asyncio.gather(*tasks)
        
        logger.info("Completed processing all videos")

async def main():
    """Función principal"""
    try:
        processor = MediaProcessor()
        await processor.process_directory()
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 