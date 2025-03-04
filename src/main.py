import os
import logging
from datetime import datetime
from src.downloader import YouTubeDownloader
from src.transcriber import WhisperTranscriber
from src.summarizer import ClaudeSummarizer

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

def process_videos(urls_file='urls.txt', whisper_model='base', api_key=None):
    """
    Procesar videos: descargar, transcribir y resumir
    """
    logger = setup_logging()
    results = {
        'download': {'status': 'not_started', 'files': []},
        'transcription': {'status': 'not_started', 'files': []},
        'summary': {'status': 'not_started', 'files': []}
    }
    
    try:
        # FASE 1: Descargar videos
        logger.info("\n" + "="*50)
        logger.info("FASE 1: DESCARGA DE VIDEOS")
        logger.info("="*50)
        
        try:
            downloader = YouTubeDownloader()
            downloaded_files = downloader.download_from_file(urls_file)
            
            if downloaded_files:
                results['download'] = {
                    'status': 'success',
                    'files': downloaded_files
                }
            else:
                results['download'] = {
                    'status': 'warning',
                    'message': 'No se descargó ningún archivo'
                }
                return results
                
        except Exception as e:
            logger.error(f"Error en la fase de descarga: {str(e)}")
            results['download'] = {
                'status': 'error',
                'error': str(e)
            }
            return results
            
        # FASE 2: Transcribir audio
        logger.info("\n" + "="*50)
        logger.info("FASE 2: TRANSCRIPCIÓN DE AUDIO")
        logger.info("="*50)
        
        try:
            transcriber = WhisperTranscriber(model_size=whisper_model)
            transcription_results = transcriber.transcribe_multiple(downloaded_files)
            
            if transcription_results:
                results['transcription'] = {
                    'status': 'success',
                    'files': transcription_results
                }
            else:
                results['transcription'] = {
                    'status': 'warning',
                    'message': 'No se generó ninguna transcripción'
                }
                return results
                
        except Exception as e:
            logger.error(f"Error en la fase de transcripción: {str(e)}")
            results['transcription'] = {
                'status': 'error',
                'error': str(e)
            }
            return results
            
        # FASE 3: Resumir transcripciones
        logger.info("\n" + "="*50)
        logger.info("FASE 3: GENERACIÓN DE RESÚMENES")
        logger.info("="*50)
        
        try:
            summarizer = ClaudeSummarizer(api_key=api_key)
            summary_results = summarizer.summarize_multiple(transcription_results)
            
            if summary_results:
                results['summary'] = {
                    'status': 'success',
                    'files': summary_results
                }
            else:
                results['summary'] = {
                    'status': 'warning',
                    'message': 'No se generó ningún resumen'
                }
                
        except Exception as e:
            logger.error(f"Error en la fase de resumen: {str(e)}")
            results['summary'] = {
                'status': 'error',
                'error': str(e)
            }
            
        # Mostrar resumen final
        logger.info("\n" + "="*50)
        logger.info("RESUMEN DEL PROCESAMIENTO")
        logger.info("="*50)
        
        for phase, result in results.items():
            status = result['status']
            if status == 'success':
                files = len(result['files'])
                logger.info(f"{phase.capitalize()}: {status} ({files} archivos)")
            else:
                message = result.get('message', result.get('error', 'Error desconocido'))
                logger.info(f"{phase.capitalize()}: {status} - {message}")
                
        return results
        
    except Exception as e:
        logger.error(f"Error general en el procesamiento: {str(e)}")
        return results

if __name__ == "__main__":
    # Verificar archivo de URLs
    if not os.path.exists('urls.txt'):
        with open('urls.txt', 'w') as f:
            f.write("https://www.youtube.com/watch?v=uDVLBmWdrds\n")
            f.write("https://www.youtube.com/watch?v=PGyMSOE9K8Y\n")
            
    # Procesar videos
    process_videos() 