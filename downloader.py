import os
import yt_dlp
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def download_video(url, output_dir='downloads'):
    """
    Descarga un video de YouTube y devuelve la ruta del archivo descargado.
    
    Args:
        url (str): URL del video de YouTube
        output_dir (str): Directorio donde se guardará el video
        
    Returns:
        str: Ruta del archivo descargado
    """
    try:
        # Crear directorio si no existe
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logging.info(f"Directorio creado: {output_dir}")
            
        info_dict = {}
        info = None
        
        # Opciones para descargar solo audio en formato mp3
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'progress_hooks': [lambda d: info_dict.update(d) if d['status'] == 'finished' else None],
            'quiet': False,  # Mostrar logs de descarga
            'no_warnings': False  # Mostrar advertencias
        }
        
        logging.info(f"Iniciando descarga de: {url}")
        
        start_time = time.time()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Primero extraemos información para verificar que se puede acceder al video
            try:
                logging.info(f"Obteniendo información del video: {url}")
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'video')
                duration = info.get('duration', 'desconocida')
                logging.info(f"Video encontrado: '{title}' (Duración: {duration}s)")
            except Exception as e:
                logging.error(f"Error al obtener información del video {url}: {str(e)}")
                raise
                
            # Luego procedemos con la descarga
            try:
                logging.info(f"Comenzando descarga de '{title}'")
                ydl.download([url])
                logging.info(f"Descarga de '{title}' completada")
            except Exception as e:
                logging.error(f"Error durante la descarga de '{title}': {str(e)}")
                raise
            
        # Construir la ruta del archivo descargado
        output_path = os.path.join(output_dir, f"{title}.mp3")
        
        # Verificar si el archivo existe
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # en MB
            end_time = time.time()
            download_time = end_time - start_time
            logging.info(f"Descarga completada: {output_path} ({file_size:.2f} MB en {download_time:.2f} segundos)")
            return output_path
        else:
            # Búsqueda alternativa del archivo
            logging.warning(f"No se encontró el archivo en la ruta esperada: {output_path}")
            logging.info("Buscando archivo descargado en el directorio...")
            
            for file in os.listdir(output_dir):
                if file.endswith(".mp3") and file.startswith(title[:20]):  # Buscar archivos similares
                    alt_path = os.path.join(output_dir, file)
                    logging.info(f"Archivo encontrado como alternativa: {alt_path}")
                    return alt_path
            
            logging.error(f"No se pudo encontrar el archivo descargado para '{title}'")
            raise FileNotFoundError(f"No se pudo encontrar el archivo descargado para '{title}'")
        
    except Exception as e:
        logging.error(f"Error al descargar {url}: {str(e)}")
        raise

def download_from_file(file_path, output_dir='downloads'):
    """
    Descarga videos de YouTube desde un archivo con URLs
    
    Args:
        file_path (str): Ruta al archivo con URLs
        output_dir (str): Directorio donde se guardarán los videos
        
    Returns:
        list: Lista con las rutas de los archivos descargados
    """
    downloaded_files = []
    
    try:
        # Verificar que el archivo existe
        if not os.path.exists(file_path):
            logging.error(f"El archivo de URLs no existe: {file_path}")
            return downloaded_files
        
        # Leer URLs del archivo
        with open(file_path, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
            
        logging.info(f"Se encontraron {len(urls)} URLs para descargar")
        
        # Procesar cada URL
        for i, url in enumerate(urls, 1):
            try:
                logging.info(f"Procesando URL {i}/{len(urls)}: {url}")
                file_path = download_video(url, output_dir)
                downloaded_files.append(file_path)
                logging.info(f"URL {i}/{len(urls)} procesada correctamente")
            except Exception as e:
                logging.error(f"Error al procesar URL {i}/{len(urls)} - {url}: {str(e)}")
                # Continuamos con la siguiente URL aunque falle esta
                
        logging.info(f"Proceso de descarga completado. {len(downloaded_files)}/{len(urls)} archivos descargados")
        return downloaded_files
        
    except Exception as e:
        logging.error(f"Error al procesar el archivo {file_path}: {str(e)}")
        return downloaded_files 