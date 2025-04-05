import os
import openai
from moviepy.editor import VideoFileClip, AudioFileClip
import logging
import tempfile
import shutil

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurar OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

def convert_video_to_audio(video_path, audio_path):
    """Convierte un archivo de video a audio MP3."""
    try:
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(audio_path)
        video.close()
        return True
    except Exception as e:
        logger.error(f"Error al convertir video a audio: {e}")
        return False

def convert_audio_to_mp3(input_path, output_path):
    """Convierte un archivo de audio a formato MP3."""
    try:
        audio = AudioFileClip(input_path)
        audio.write_audiofile(output_path)
        audio.close()
        return True
    except Exception as e:
        logger.error(f"Error al convertir audio a MP3: {e}")
        return False

def transcribe_audio(audio_path):
    """Transcribe un archivo de audio usando la API de OpenAI."""
    try:
        with open(audio_path, "rb") as audio_file:
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return response
    except Exception as e:
        logger.error(f"Error al transcribir audio: {e}")
        return None

def transcribe_files():
    """Procesa los archivos en el directorio Transcript."""
    logger.info("Iniciando proceso de transcripción...\n")
    
    # Crear directorios si no existen
    os.makedirs("Transcript", exist_ok=True)
    os.makedirs("Transcripciones", exist_ok=True)
    
    # Crear directorio temporal
    with tempfile.TemporaryDirectory() as temp_dir:
        # Procesar cada archivo en el directorio Transcript
        for filename in os.listdir("Transcript"):
            input_path = os.path.join("Transcript", filename)
            logger.info(f"Procesando: {filename}")
            
            # Determinar el tipo de archivo y convertir si es necesario
            name, ext = os.path.splitext(filename)
            temp_audio_path = os.path.join(temp_dir, f"{name}.mp3")
            
            if ext.lower() in ['.mp4', '.avi', '.mov', '.webm']:
                if not convert_video_to_audio(input_path, temp_audio_path):
                    continue
            elif ext.lower() not in ['.mp3']:
                if not convert_audio_to_mp3(input_path, temp_audio_path):
                    continue
            else:
                temp_audio_path = input_path
            
            # Transcribir audio
            logger.info(f"Transcribiendo audio: {input_path}")
            transcription = transcribe_audio(temp_audio_path)
            
            if transcription:
                # Guardar transcripción
                output_path = os.path.join("Transcripciones", f"{name}.txt")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(transcription)
                logger.info(f"Transcripción guardada en: {output_path}\n")
            else:
                logger.error(f"Error procesando {input_path}\n")
    
    logger.info("Proceso completado!")

if __name__ == "__main__":
    transcribe_files() 