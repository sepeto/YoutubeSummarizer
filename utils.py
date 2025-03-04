import os
import logging
from dotenv import load_dotenv

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_env_variables():
    """
    Carga variables de entorno desde el archivo .env
    
    Returns:
        dict: Diccionario con las variables de entorno relevantes
    """
    # Cargar variables de entorno desde .env
    load_dotenv()
    
    # Recopilar configuraciones
    config = {
        'anthropic_api_key': os.environ.get('ANTHROPIC_API_KEY'),
        'whisper_model': os.environ.get('WHISPER_MODEL', 'base'),
        'output_base_dir': os.environ.get('OUTPUT_BASE_DIR', 'output')
    }
    
    # Verificar API key
    if not config['anthropic_api_key']:
        logging.warning("No se encontró ANTHROPIC_API_KEY en .env o variables de entorno")
        
    return config

def create_directory_structure(base_dir='output'):
    """
    Crea la estructura de directorios para el proyecto
    
    Args:
        base_dir (str): Directorio base
        
    Returns:
        dict: Diccionario con las rutas a los directorios
    """
    directories = {
        'downloads': os.path.join(base_dir, 'downloads'),
        'transcriptions': os.path.join(base_dir, 'transcriptions'),
        'summaries': os.path.join(base_dir, 'summaries')
    }
    
    # Crear directorios
    for dir_path in directories.values():
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logging.info(f"Directorio creado: {dir_path}")
            
    return directories

def save_urls_to_file(urls, file_path='urls.txt'):
    """
    Guarda una lista de URLs en un archivo
    
    Args:
        urls (list): Lista de URLs
        file_path (str): Ruta del archivo donde guardar las URLs
    """
    try:
        with open(file_path, 'w') as f:
            for url in urls:
                f.write(f"{url}\n")
                
        logging.info(f"URLs guardadas en: {file_path}")
        
    except Exception as e:
        logging.error(f"Error al guardar URLs en {file_path}: {str(e)}")
        raise

def print_summary(summary_results):
    """
    Imprime un resumen del procesamiento
    
    Args:
        summary_results (list): Lista de resultados de resumen
    """
    print("\n" + "="*50)
    print("RESUMEN DEL PROCESAMIENTO")
    print("="*50)
    
    for i, result in enumerate(summary_results, 1):
        print(f"\nVIDEO {i}:")
        print(f"Archivo: {os.path.basename(result['original_file'])}")
        print(f"Transcripción: {os.path.basename(result['transcription_file'])}")
        print(f"Resumen: {os.path.basename(result['summary_file'])}")
        print("\nTaglines:")
        print(result['summary_text'])
        print("-"*50) 