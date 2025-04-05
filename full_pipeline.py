import os
import sys
import time
import logging
import traceback
import asyncio
import dotenv
import openai
from moviepy.editor import VideoFileClip
from utils.downloader import YoutubeDownloader

# Cargar variables de entorno (API keys)
dotenv.load_dotenv()

# Configurar la API key de OpenAI desde la variable de entorno
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('full_pipeline.log')
    ]
)
logger = logging.getLogger(__name__)

# Directorios del pipeline
DIRS = {
    "urls": "test_urls.txt",  # Archivo con URLs
    "downloads": "Descargas",    # Videos descargados
    "audio": "Transcript",      # Audios convertidos
    "transcripts": "Transcripciones",  # Transcripciones
    "summaries": "Resumenes"     # Resúmenes
}

def ensure_directories():
    """Asegura que existan todos los directorios necesarios"""
    for directory in list(DIRS.values())[1:]:  # Todos menos el archivo de URLs
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"Directorio asegurado: {directory}")

def already_exists(filename, directory, extension=None):
    """Verifica si un archivo ya existe en el directorio especificado"""
    base_name = os.path.splitext(filename)[0]
    if extension:
        check_file = os.path.join(directory, f"{base_name}{extension}")
    else:
        # Buscar cualquier archivo con el mismo nombre base
        for file in os.listdir(directory):
            if os.path.splitext(file)[0] == base_name:
                return True
        return False
    
    return os.path.exists(check_file)

async def download_videos():
    """Paso 1: Descarga videos desde URLs en el archivo"""
    logger.info("=== PASO 1: DESCARGA DE VIDEOS ===")
    
    # Crear directorio si no existe
    os.makedirs(DIRS["downloads"], exist_ok=True)
    
    # Inicializar el descargador
    downloader = YoutubeDownloader()
    
    # Descargar desde archivo
    try:
        await downloader.download_from_file(DIRS["urls"])
    except Exception as e:
        logger.error(f"Error en la descarga de videos: {str(e)}")
        logger.error(traceback.format_exc())

def convert_videos_to_audio():
    """Paso 2: Convierte los videos descargados a audio MP3"""
    logger.info("=== PASO 2: CONVERSIÓN A AUDIO ===")
    
    # Obtener lista de videos
    videos = [f for f in os.listdir(DIRS["downloads"]) if f.endswith(('.mp4', '.webm', '.mkv'))]
    
    if not videos:
        logger.info("No hay videos para convertir")
        return
    
    logger.info(f"Encontrados {len(videos)} videos para convertir")
    
    # Contadores
    processed = 0
    failed = 0
    skipped = 0
    
    # Procesar cada video
    for video in videos:
        video_path = os.path.join(DIRS["downloads"], video)
        base_name = os.path.splitext(video)[0]
        audio_path = os.path.join(DIRS["audio"], f"{base_name}.mp3")
        
        # Verificar si ya existe
        if os.path.exists(audio_path):
            logger.info(f"Omitiendo (ya convertido): {video}")
            skipped += 1
            continue
        
        logger.info(f"Convirtiendo video a audio: {video}")
        
        try:
            # Convertir a MP3
            video_clip = VideoFileClip(video_path)
            audio = video_clip.audio
            audio.write_audiofile(audio_path, logger=None)  # Silenciar logs de moviepy
            video_clip.close()
            audio.close()
            
            logger.info(f"Audio guardado: {os.path.basename(audio_path)}")
            processed += 1
            
        except Exception as e:
            logger.error(f"Error al convertir {video}: {str(e)}")
            logger.error(traceback.format_exc())
            failed += 1
    
    logger.info(f"Conversión completa: {processed} procesados, {failed} fallidos, {skipped} omitidos")

def transcribe_audio(audio_path):
    """Transcribe un archivo de audio usando la API de OpenAI"""
    try:
        logger.info(f"Enviando audio a OpenAI para transcripción: {os.path.basename(audio_path)}")
        with open(audio_path, "rb") as audio_file:
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return response
    except Exception as e:
        logger.error(f"Error al transcribir audio: {str(e)}")
        return None

def transcribe_files():
    """Paso 3: Transcribe los archivos de audio"""
    logger.info("=== PASO 3: TRANSCRIPCIÓN DE AUDIO ===")
    
    # Obtener archivos de audio
    audio_files = [f for f in os.listdir(DIRS["audio"]) if f.endswith('.mp3')]
    
    if not audio_files:
        logger.info("No hay archivos de audio para transcribir")
        return
    
    logger.info(f"Encontrados {len(audio_files)} archivos de audio")
    
    # Contadores
    processed = 0
    failed = 0
    skipped = 0
    
    # Procesar cada archivo
    for audio_file in audio_files:
        audio_path = os.path.join(DIRS["audio"], audio_file)
        base_name = os.path.splitext(audio_file)[0]
        transcript_path = os.path.join(DIRS["transcripts"], f"{base_name}.txt")
        
        # Verificar si ya existe
        if os.path.exists(transcript_path):
            logger.info(f"Omitiendo (ya transcrito): {audio_file}")
            skipped += 1
            continue
        
        logger.info(f"Transcribiendo audio: {audio_file}")
        
        try:
            # Transcribir
            transcription = transcribe_audio(audio_path)
            
            if transcription:
                # Guardar transcripción
                with open(transcript_path, "w", encoding="utf-8") as f:
                    f.write(transcription)
                logger.info(f"Transcripción guardada: {os.path.basename(transcript_path)}")
                processed += 1
            else:
                logger.error(f"La transcripción para {audio_file} falló o está vacía")
                failed += 1
        except Exception as e:
            logger.error(f"Error procesando {audio_file}: {str(e)}")
            logger.error(traceback.format_exc())
            failed += 1
    
    logger.info(f"Transcripción completa: {processed} procesados, {failed} fallidos, {skipped} omitidos")

def generate_summary(text):
    """Genera un resumen usando la API de OpenAI"""
    try:
        # Cargar el prompt para resúmenes
        prompt_path = "summary_prompt.txt"
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt = f.read().strip()
        else:
            prompt = "Resume el siguiente texto en un máximo de 3 párrafos conservando las ideas principales:"
        
        # Llamar a la API
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"{prompt}\n\n{text}",
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].text.strip()
    except Exception as e:
        logger.error(f"Error al generar resumen: {str(e)}")
        return None

def generate_summaries():
    """Paso 4: Genera resúmenes de las transcripciones"""
    logger.info("=== PASO 4: GENERACIÓN DE RESÚMENES ===")
    
    # Obtener archivos de transcripción
    transcript_files = [f for f in os.listdir(DIRS["transcripts"]) if f.endswith('.txt')]
    
    if not transcript_files:
        logger.info("No hay transcripciones para resumir")
        return
    
    logger.info(f"Encontradas {len(transcript_files)} transcripciones")
    
    # Contadores
    processed = 0
    failed = 0
    skipped = 0
    
    # Procesar cada archivo
    for transcript_file in transcript_files:
        transcript_path = os.path.join(DIRS["transcripts"], transcript_file)
        summary_path = os.path.join(DIRS["summaries"], transcript_file)
        
        # Verificar si ya existe
        if os.path.exists(summary_path):
            logger.info(f"Omitiendo (ya resumido): {transcript_file}")
            skipped += 1
            continue
        
        logger.info(f"Generando resumen para: {transcript_file}")
        
        try:
            # Leer transcripción
            with open(transcript_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Verificar longitud
            if len(text) < 10:
                logger.warning(f"Texto demasiado corto para resumir: {transcript_file}")
                failed += 1
                continue
            
            # Generar resumen
            summary = generate_summary(text)
            
            if summary:
                # Guardar resumen
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write(summary)
                logger.info(f"Resumen guardado: {os.path.basename(summary_path)}")
                processed += 1
            else:
                logger.error(f"No se pudo generar resumen para: {transcript_file}")
                failed += 1
        except Exception as e:
            logger.error(f"Error procesando {transcript_file}: {str(e)}")
            logger.error(traceback.format_exc())
            failed += 1
    
    logger.info(f"Generación de resúmenes completa: {processed} procesados, {failed} fallidos, {skipped} omitidos")

async def main():
    """Ejecuta todo el pipeline de procesamiento"""
    start_time = time.time()
    logger.info("=== INICIANDO PIPELINE COMPLETO ===")
    
    # Asegurar que existan los directorios
    ensure_directories()
    
    try:
        # Paso 1: Descargar videos
        await download_videos()
        
        # Paso 2: Convertir videos a audio
        convert_videos_to_audio()
        
        # Paso 3: Transcribir audio
        transcribe_files()
        
        # Paso 4: Generar resúmenes
        generate_summaries()
        
    except Exception as e:
        logger.error(f"Error en el pipeline: {str(e)}")
        logger.error(traceback.format_exc())
    
    elapsed_time = time.time() - start_time
    logger.info(f"=== PIPELINE COMPLETO FINALIZADO en {elapsed_time:.2f} segundos ===")

if __name__ == "__main__":
    asyncio.run(main()) 