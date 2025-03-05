import os
import logging
import sys
from datetime import datetime
from src.downloader import YouTubeDownloader

def setup_logging():
    """Configurar logging principal"""
    # Configurar codificación por defecto para sys.stdout
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    
    # Crear directorio de logs si no existe
    log_dir = 'output/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # Configurar logging
    log_file = os.path.join(log_dir, f'main_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    logger = logging.getLogger('main')
    logger.setLevel(logging.INFO)
    
    # Limpiar handlers existentes
    logger.handlers = []
    
    # Handler para archivo con encoding UTF-8
    file_handler = logging.FileHandler(log_file, encoding='utf-8', errors='replace')
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # Handler para consola con encoding UTF-8
    console_handler = logging.StreamHandler(sys.stdout)
    console_format = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    return logger

def process_videos(urls_file='urls.txt'):
    """
    Descargar videos de YouTube
    """
    logger = setup_logging()
    
    try:
        # FASE 1: Descargar videos
        logger.info("\n" + "="*50)
        logger.info("DESCARGA DE VIDEOS")
        logger.info("="*50)
        
        downloader = YouTubeDownloader()
        downloaded_files = downloader.download_from_file(urls_file)
        
        if downloaded_files:
            logger.info("\nDescargas completadas:")
            for file in downloaded_files:
                logger.info(f"- {file}")
        else:
            logger.warning("No se descargó ningún archivo")
            
    except Exception as e:
        logger.error(f"Error en la descarga: {str(e)}")
        raise

if __name__ == "__main__":
    # Verificar archivo de URLs
    if not os.path.exists('urls.txt'):
        with open('urls.txt', 'w', encoding='utf-8') as f:
            f.write("https://www.youtube.com/watch?v=uDVLBmWdrds\n")
            f.write("https://www.youtube.com/watch?v=PGyMSOE9K8Y\n")
            
    # Procesar videos
    process_videos() 