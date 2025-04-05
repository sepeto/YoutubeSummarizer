import os
from moviepy.editor import VideoFileClip
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def convert_video_to_mp3(video_path, output_path):
    try:
        video = VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile(output_path)
        video.close()
        audio.close()
        return True
    except Exception as e:
        logger.error(f"Error converting {video_path}: {str(e)}")
        return False

def main():
    # Directorios
    downloads_dir = "Descargas"
    transcript_dir = "Transcript"
    
    # Crear directorio de transcripción si no existe
    os.makedirs(transcript_dir, exist_ok=True)
    
    # Obtener lista de videos
    video_files = [f for f in os.listdir(downloads_dir) if f.endswith(('.mp4', '.webm'))]
    
    if not video_files:
        logger.info("No se encontraron videos para convertir")
        return
    
    logger.info(f"Encontrados {len(video_files)} videos para convertir")
    
    # Procesar cada video
    successful = 0
    for video_file in video_files:
        video_path = os.path.join(downloads_dir, video_file)
        output_file = os.path.splitext(video_file)[0] + '.mp3'
        output_path = os.path.join(transcript_dir, output_file)
        
        logger.info(f"Convirtiendo: {video_file}")
        if convert_video_to_mp3(video_path, output_path):
            successful += 1
            logger.info(f"Convertido exitosamente: {output_file}")
    
    logger.info(f"Proceso completado: {successful} de {len(video_files)} videos convertidos")

if __name__ == "__main__":
    main() 