import os
import logging
from datetime import datetime
from src.downloader import YouTubeDownloader

def setup_logging():
    """Configurar logging principal"""
    # Crear directorio de logs si no existe
    log_dir = 'output/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # Configurar logging
    log_file = os.path.join(log_dir, f'main_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('main')

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

if __name__ == "__main__":
    # Verificar archivo de URLs
    if not os.path.exists('urls.txt'):
        with open('urls.txt', 'w') as f:
            f.write("https://www.youtube.com/watch?v=uDVLBmWdrds\n")
            f.write("https://www.youtube.com/watch?v=PGyMSOE9K8Y\n")
            
    # Procesar videos
    process_videos() 