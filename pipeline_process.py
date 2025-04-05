import os
import logging
import time
import sys
import traceback
import dotenv
from summarize import Summarizer

# Cargar variables de entorno
dotenv.load_dotenv()

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('pipeline.log')
    ]
)
logger = logging.getLogger(__name__)

def already_processed(source_file, target_dir, target_ext=".txt"):
    """Verifica si un archivo ya ha sido procesado (existe en el directorio destino)"""
    base_name = os.path.splitext(os.path.basename(source_file))[0]
    target_file = os.path.join(target_dir, f"{base_name}{target_ext}")
    return os.path.exists(target_file)

def dummy_transcribe_audio(audio_path):
    """Función de simulación de transcripción para pruebas"""
    # En producción aquí se llamaría a la API de OpenAI
    logger.info(f"Simulando transcripción de: {audio_path}")
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    return f"Transcripción simulada para {base_name}. Este es un texto de prueba para simular una transcripción real. Se puede utilizar para verificar el flujo de trabajo sin necesidad de usar la API de OpenAI. En un entorno de producción, esta función sería reemplazada por la llamada real a la API que devolvería el texto transcrito del audio o video proporcionado."

def process_transcription():
    """Procesa todos los archivos de audio que no han sido transcritos aún"""
    logger.info("=== INICIANDO PROCESO DE TRANSCRIPCIÓN ===")
    
    # Verificar que existan los directorios
    os.makedirs("Transcript", exist_ok=True)
    os.makedirs("Transcripciones", exist_ok=True)
    
    # Obtener archivos de audio
    audio_files = [f for f in os.listdir("Transcript") if f.endswith(('.mp3', '.wav', '.m4a'))]
    
    if not audio_files:
        logger.info("No hay archivos de audio para transcribir")
        return
    
    logger.info(f"Encontrados {len(audio_files)} archivos de audio")
    
    # Contador de procesados
    processed = 0
    failed = 0
    skipped = 0
    
    # Procesar cada archivo
    for audio_file in audio_files:
        audio_path = os.path.join("Transcript", audio_file)
        base_name = os.path.splitext(audio_file)[0]
        output_path = os.path.join("Transcripciones", f"{base_name}.txt")
        
        # Verificar si ya existe
        if already_processed(audio_file, "Transcripciones"):
            logger.info(f"Omitiendo (ya procesado): {audio_file}")
            skipped += 1
            continue
        
        logger.info(f"Transcribiendo: {audio_file}")
        
        try:
            # Usar transcripción simulada para pruebas
            transcription = dummy_transcribe_audio(audio_path)
            
            if transcription:
                # Guardar transcripción
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(transcription)
                logger.info(f"Transcripción guardada en: {output_path}")
                processed += 1
            else:
                logger.error(f"Error al transcribir {audio_file}")
                failed += 1
        except Exception as e:
            logger.error(f"Error procesando {audio_file}: {str(e)}")
            logger.error(traceback.format_exc())
            failed += 1
    
    logger.info(f"Transcripción completa: {processed} procesados, {failed} fallidos, {skipped} omitidos")
    return processed > 0  # Retorna True si se procesó al menos un archivo

def dummy_generate_summary(text):
    """Función de simulación de resumen para pruebas"""
    # En producción aquí se llamaría a la API de OpenAI
    logger.info(f"Simulando generación de resumen para texto de {len(text)} caracteres")
    return f"Resumen simulado: {text[:100]}... [Texto resumido de {len(text)} caracteres]"

def process_summarization():
    """Procesa todos los archivos de transcripción que no han sido resumidos aún"""
    logger.info("=== INICIANDO PROCESO DE RESUMEN ===")
    
    # Verificar que existan los directorios
    os.makedirs("Transcripciones", exist_ok=True)
    os.makedirs("Resumenes", exist_ok=True)
    
    # Obtener archivos de transcripción
    transcript_files = [f for f in os.listdir("Transcripciones") if f.endswith('.txt')]
    
    if not transcript_files:
        logger.info("No hay archivos de transcripción para resumir")
        return
    
    logger.info(f"Encontrados {len(transcript_files)} archivos de transcripción")
    
    # Contador de procesados
    processed = 0
    failed = 0
    skipped = 0
    
    # Procesar cada archivo
    for transcript_file in transcript_files:
        input_path = os.path.join("Transcripciones", transcript_file)
        output_path = os.path.join("Resumenes", transcript_file)
        
        # Verificar si ya existe
        if already_processed(transcript_file, "Resumenes"):
            logger.info(f"Omitiendo (ya procesado): {transcript_file}")
            skipped += 1
            continue
        
        logger.info(f"Resumiendo: {transcript_file}")
        
        try:
            # Leer el archivo
            with open(input_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            # Usar resumen simulado para pruebas
            final_summary = dummy_generate_summary(text)
            
            # Guardar el resumen
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_summary)
            
            logger.info(f"Resumen guardado en: {output_path}")
            processed += 1
            
        except Exception as e:
            logger.error(f"Error procesando {transcript_file}: {str(e)}")
            logger.error(traceback.format_exc())
            failed += 1
    
    logger.info(f"Resumen completo: {processed} procesados, {failed} fallidos, {skipped} omitidos")

def main():
    """Función principal que ejecuta el pipeline completo"""
    start_time = time.time()
    logger.info("=== INICIANDO PIPELINE DE PROCESAMIENTO ===")
    
    # Primero transcribir todos los archivos
    process_transcription()
    
    # Luego resumir todos los archivos
    process_summarization()
    
    elapsed_time = time.time() - start_time
    logger.info(f"=== PIPELINE COMPLETADO en {elapsed_time:.2f} segundos ===")

if __name__ == "__main__":
    main() 