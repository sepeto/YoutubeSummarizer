import os
import logging
import concurrent.futures
import psutil
import shutil
import hashlib
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from src.downloader import YouTubeDownloader
from src.transcriber import WhisperTranscriber
from src.summarizer import ClaudeSummarizer
from src import config

def setup_logging():
    """Configurar logging principal"""
    # Crear directorio de logs si no existe
    log_dir = config.LOG_DIR
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

def ensure_directories():
    """Asegurar que existen todos los directorios necesarios"""
    dirs = [
        config.CACHE_DIR,
        config.DOWNLOAD_DIR,
        config.TRANSCRIPTION_DIR,
        config.SUMMARY_DIR,
        config.LOG_DIR,
        config.BACKUP_DIR,
        config.COMPRESSED_DIR
    ]
    
    for dir_path in dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logging.info(f"Directorio creado: {dir_path}")

def check_resources():
    """Verificar recursos del sistema antes de procesar"""
    logger = logging.getLogger('main')
    
    if not config.ENABLE_RESOURCE_MONITORING:
        return True
        
    # Verificar espacio en disco
    disk_usage = psutil.disk_usage('/')
    disk_percent = disk_usage.percent
    
    # Verificar uso de memoria
    memory_usage = psutil.virtual_memory()
    memory_percent = memory_usage.percent
    
    logger.info(f"Uso de disco: {disk_percent:.1f}%, Uso de memoria: {memory_percent:.1f}%")
    
    if disk_percent > config.MAX_DISK_USAGE_PERCENT:
        logger.warning(f"Uso de disco crítico: {disk_percent:.1f}% > {config.MAX_DISK_USAGE_PERCENT}%")
        return False
        
    if memory_percent > config.MAX_MEMORY_USAGE_PERCENT:
        logger.warning(f"Uso de memoria crítico: {memory_percent:.1f}% > {config.MAX_MEMORY_USAGE_PERCENT}%")
        return False
        
    return True

def validate_urls(urls):
    """Validar URLs de YouTube y filtrar las no válidas"""
    import re
    
    logger = logging.getLogger('main')
    valid_urls = []
    invalid_urls = []
    
    # Regex para validar URLs de YouTube
    youtube_regex = r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})(&.*)?$'
    youtube_playlist_regex = r'^(https?://)?(www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)(&.*)?$'
    
    for url in urls:
        url = url.strip()
        if not url:
            continue
            
        # Verificar si es una URL de video de YouTube
        if re.match(youtube_regex, url):
            valid_urls.append(url)
        # Verificar si es una URL de playlist de YouTube
        elif re.match(youtube_playlist_regex, url) and config.ALLOW_PLAYLISTS:
            logger.info(f"Playlist detectada: {url}")
            valid_urls.append(url)
        else:
            logger.warning(f"URL no válida: {url}")
            invalid_urls.append(url)
    
    if invalid_urls:
        logger.warning(f"Se encontraron {len(invalid_urls)} URLs no válidas")
        
    return valid_urls

def create_cache_key(url):
    """Crear clave de caché única para una URL"""
    return hashlib.md5(url.encode()).hexdigest()

def check_cache(url, cache_type):
    """Verificar si existe caché para una URL y tipo específico"""
    if not config.ENABLE_CACHE:
        return None
        
    cache_key = create_cache_key(url)
    cache_file = os.path.join(config.CACHE_DIR, f"{cache_key}_{cache_type}.json")
    
    if os.path.exists(cache_file):
        # Verificar si el caché ha expirado
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
        expiry_time = datetime.now() - timedelta(days=config.CACHE_EXPIRY_DAYS)
        
        if file_time > expiry_time:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error leyendo caché: {str(e)}")
                return None
    
    return None

def save_to_cache(url, cache_type, data):
    """Guardar datos en caché"""
    if not config.ENABLE_CACHE:
        return
        
    cache_key = create_cache_key(url)
    cache_file = os.path.join(config.CACHE_DIR, f"{cache_key}_{cache_type}.json")
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Error guardando caché: {str(e)}")

def compress_files(files, base_name):
    """Comprimir archivos generados"""
    if not config.ENABLE_COMPRESSION:
        return None
        
    logger = logging.getLogger('main')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(config.COMPRESSED_DIR, f"{base_name}_{timestamp}")
    
    try:
        if config.COMPRESSION_FORMAT == "zip":
            import zipfile
            output_file += ".zip"
            
            with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=config.COMPRESSION_LEVEL) as zipf:
                for file in files:
                    if os.path.exists(file):
                        arcname = os.path.basename(file)
                        zipf.write(file, arcname)
                        
        elif config.COMPRESSION_FORMAT == "tar.gz":
            import tarfile
            output_file += ".tar.gz"
            
            with tarfile.open(output_file, "w:gz", compresslevel=config.COMPRESSION_LEVEL) as tar:
                for file in files:
                    if os.path.exists(file):
                        arcname = os.path.basename(file)
                        tar.add(file, arcname=arcname)
        
        logger.info(f"Archivos comprimidos en: {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Error comprimiendo archivos: {str(e)}")
        return None

def create_backup():
    """Crear backup de los directorios importantes"""
    if not config.ENABLE_AUTO_BACKUP:
        return
        
    logger = logging.getLogger('main')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(config.BACKUP_DIR, f"backup_{timestamp}")
    
    try:
        os.makedirs(backup_dir)
        
        # Directorios a respaldar
        dirs_to_backup = [
            config.DOWNLOAD_DIR,
            config.TRANSCRIPTION_DIR,
            config.SUMMARY_DIR
        ]
        
        for dir_path in dirs_to_backup:
            if os.path.exists(dir_path):
                dir_name = os.path.basename(dir_path)
                backup_path = os.path.join(backup_dir, dir_name)
                shutil.copytree(dir_path, backup_path)
                
        logger.info(f"Backup creado en: {backup_dir}")
        
        # Eliminar backups antiguos si se excede el límite
        backups = sorted([d for d in os.listdir(config.BACKUP_DIR) if d.startswith("backup_")])
        if len(backups) > config.MAX_BACKUPS:
            for old_backup in backups[:-config.MAX_BACKUPS]:
                old_path = os.path.join(config.BACKUP_DIR, old_backup)
                shutil.rmtree(old_path)
                logger.info(f"Backup antiguo eliminado: {old_path}")
                
    except Exception as e:
        logger.error(f"Error creando backup: {str(e)}")

def process_video(url, whisper_model='base', api_key=None):
    """Procesar un solo video: descargar, transcribir y resumir"""
    logger = logging.getLogger('main')
    
    # Verificar caché
    cache_result = check_cache(url, "full_process")
    if cache_result:
        logger.info(f"Usando resultado en caché para: {url}")
        return cache_result
    
    result = {
        'url': url,
        'download': {'status': 'not_started'},
        'transcription': {'status': 'not_started'},
        'summary': {'status': 'not_started'}
    }
    
    try:
        # FASE 1: Descargar video
        logger.info(f"Descargando: {url}")
        
        try:
            downloader = YouTubeDownloader()
            downloaded_file = downloader.download_single(url)
            
            if downloaded_file:
                result['download'] = {
                    'status': 'success',
                    'file': downloaded_file
                }
            else:
                result['download'] = {
                    'status': 'warning',
                    'message': 'No se pudo descargar el archivo'
                }
                return result
                
        except Exception as e:
            logger.error(f"Error en la descarga de {url}: {str(e)}")
            result['download'] = {
                'status': 'error',
                'error': str(e)
            }
            return result
            
        # FASE 2: Transcribir audio
        logger.info(f"Transcribiendo: {downloaded_file}")
        
        try:
            transcriber = WhisperTranscriber(model_size=whisper_model)
            transcription_path, transcription_text = transcriber.transcribe_audio(downloaded_file)
            
            if transcription_text:
                result['transcription'] = {
                    'status': 'success',
                    'file': transcription_path,
                    'text': transcription_text
                }
            else:
                result['transcription'] = {
                    'status': 'warning',
                    'message': 'No se generó transcripción'
                }
                return result
                
        except Exception as e:
            logger.error(f"Error en la transcripción de {downloaded_file}: {str(e)}")
            result['transcription'] = {
                'status': 'error',
                'error': str(e)
            }
            return result
            
        # FASE 3: Resumir transcripción
        logger.info(f"Resumiendo transcripción: {transcription_path}")
        
        try:
            summarizer = ClaudeSummarizer(api_key=api_key)
            summary_path, summary_text = summarizer.summarize_text(transcription_text, os.path.basename(downloaded_file).split('.')[0])
            
            if summary_text:
                result['summary'] = {
                    'status': 'success',
                    'file': summary_path,
                    'text': summary_text
                }
            else:
                result['summary'] = {
                    'status': 'warning',
                    'message': 'No se generó resumen'
                }
                
        except Exception as e:
            logger.error(f"Error en el resumen de {transcription_path}: {str(e)}")
            result['summary'] = {
                'status': 'error',
                'error': str(e)
            }
            
        # Guardar en caché
        save_to_cache(url, "full_process", result)
        
        return result
        
    except Exception as e:
        logger.error(f"Error general procesando {url}: {str(e)}")
        return result

def process_videos_parallel(urls_file='urls.txt', whisper_model='base', api_key=None):
    """
    Procesar videos en paralelo usando ThreadPoolExecutor
    """
    logger = setup_logging()
    ensure_directories()
    
    # Verificar recursos del sistema
    if not check_resources():
        logger.error("Recursos del sistema insuficientes para continuar")
        return {
            'status': 'error',
            'message': 'Recursos del sistema insuficientes'
        }
    
    # Leer URLs del archivo
    try:
        with open(urls_file, 'r', encoding='utf-8') as f:
            urls = f.readlines()
    except Exception as e:
        logger.error(f"Error leyendo archivo de URLs: {str(e)}")
        return {
            'status': 'error',
            'message': f"Error leyendo archivo de URLs: {str(e)}"
        }
    
    # Validar URLs
    if config.VALIDATE_URLS:
        urls = validate_urls(urls)
        if not urls:
            logger.warning("No se encontraron URLs válidas")
            return {
                'status': 'warning',
                'message': 'No se encontraron URLs válidas'
            }
    
    # Crear backup antes de procesar
    create_backup()
    
    results = []
    max_workers = config.MAX_WORKERS if config.ENABLE_PARALLEL else 1
    
    logger.info(f"Iniciando procesamiento de {len(urls)} URLs con {max_workers} workers")
    
    start_time = time.time()
    
    # Procesar en paralelo o secuencial
    if config.ENABLE_PARALLEL:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(process_video, url.strip(), whisper_model, api_key): url.strip() for url in urls}
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Completado: {url}")
                except Exception as e:
                    logger.error(f"Error procesando {url}: {str(e)}")
                    results.append({
                        'url': url,
                        'status': 'error',
                        'error': str(e)
                    })
    else:
        for url in urls:
            url = url.strip()
            if url:
                try:
                    result = process_video(url, whisper_model, api_key)
                    results.append(result)
                    logger.info(f"Completado: {url}")
                except Exception as e:
                    logger.error(f"Error procesando {url}: {str(e)}")
                    results.append({
                        'url': url,
                        'status': 'error',
                        'error': str(e)
                    })
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Comprimir archivos generados
    all_files = []
    for result in results:
        if 'download' in result and 'file' in result['download']:
            all_files.append(result['download']['file'])
        if 'transcription' in result and 'file' in result['transcription']:
            all_files.append(result['transcription']['file'])
        if 'summary' in result and 'file' in result['summary']:
            all_files.append(result['summary']['file'])
    
    if all_files:
        compress_files(all_files, "process_results")
    
    # Mostrar resumen final
    logger.info("\n" + "="*50)
    logger.info("RESUMEN DEL PROCESAMIENTO")
    logger.info("="*50)
    
    success_count = sum(1 for r in results if r.get('summary', {}).get('status') == 'success')
    warning_count = sum(1 for r in results if r.get('summary', {}).get('status') == 'warning')
    error_count = sum(1 for r in results if r.get('summary', {}).get('status') == 'error')
    
    logger.info(f"Total URLs procesadas: {len(results)}")
    logger.info(f"Éxitos: {success_count}")
    logger.info(f"Advertencias: {warning_count}")
    logger.info(f"Errores: {error_count}")
    logger.info(f"Tiempo total: {total_time:.2f} segundos")
    
    return {
        'status': 'success',
        'results': results,
        'stats': {
            'total': len(results),
            'success': success_count,
            'warning': warning_count,
            'error': error_count,
            'time': total_time
        }
    }

def process_videos(urls_file='urls.txt', whisper_model='base', api_key=None):
    """
    Función de compatibilidad para mantener la API anterior
    Ahora usa la versión con procesamiento paralelo
    """
    return process_videos_parallel(urls_file, whisper_model, api_key)

if __name__ == "__main__":
    # Verificar archivo de URLs
    if not os.path.exists('urls.txt'):
        with open('urls.txt', 'w') as f:
            f.write("https://www.youtube.com/watch?v=uDVLBmWdrds\n")
            f.write("https://www.youtube.com/watch?v=PGyMSOE9K8Y\n")
            
    # Procesar videos
    process_videos()