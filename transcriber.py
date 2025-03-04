import os
import whisper
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def transcribe_audio(audio_path, output_dir='transcriptions', model_size='base'):
    """
    Transcribe un archivo de audio utilizando Whisper.
    
    Args:
        audio_path (str): Ruta al archivo de audio
        output_dir (str): Directorio donde se guardará la transcripción
        model_size (str): Tamaño del modelo de Whisper ('tiny', 'base', 'small', 'medium', 'large')
        
    Returns:
        str: Ruta al archivo de transcripción
        str: Texto transcrito
    """
    try:
        # Crear directorio si no existe
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Obtener nombre base del archivo
        base_name = os.path.basename(audio_path)
        file_name = os.path.splitext(base_name)[0]
        
        # Cargar modelo Whisper
        logging.info(f"Cargando modelo Whisper {model_size}...")
        model = whisper.load_model(model_size)
        
        # Transcribir audio
        logging.info(f"Transcribiendo: {audio_path}")
        result = model.transcribe(audio_path)
        transcription = result["text"]
        
        # Guardar transcripción en archivo
        output_path = os.path.join(output_dir, f"{file_name}.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(transcription)
            
        logging.info(f"Transcripción completada y guardada en: {output_path}")
        
        return output_path, transcription
        
    except Exception as e:
        logging.error(f"Error al transcribir {audio_path}: {str(e)}")
        raise

def transcribe_multiple(audio_files, output_dir='transcriptions', model_size='base'):
    """
    Transcribe múltiples archivos de audio.
    
    Args:
        audio_files (list): Lista de rutas a archivos de audio
        output_dir (str): Directorio donde se guardarán las transcripciones
        model_size (str): Tamaño del modelo de Whisper

    Returns:
        list: Lista de diccionarios con rutas de archivos y transcripciones
    """
    results = []
    
    for audio_file in audio_files:
        try:
            output_path, transcription = transcribe_audio(audio_file, output_dir, model_size)
            results.append({
                'audio_file': audio_file,
                'transcription_file': output_path,
                'transcription_text': transcription
            })
        except Exception as e:
            logging.error(f"Error al procesar {audio_file}: {str(e)}")
    
    return results 