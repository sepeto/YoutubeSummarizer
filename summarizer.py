import os
import logging
from anthropic import Anthropic

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def summarize_text(text, output_dir='summaries', api_key=None):
    """
    Resumir texto utilizando Claude 3.7 para crear taglines
    
    Args:
        text (str): Texto a resumir
        output_dir (str): Directorio donde se guardará el resumen
        api_key (str): API key de Anthropic
        
    Returns:
        str: Ruta al archivo de resumen
        str: Texto resumido con taglines
    """
    try:
        # Verificar que tenemos API key
        if not api_key:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("Se requiere una API key de Anthropic. Proporciónala como argumento o configura la variable de entorno ANTHROPIC_API_KEY")
        
        # Crear directorio si no existe
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Inicializar cliente de Anthropic
        client = Anthropic(api_key=api_key)
        
        # Construir prompt para Claude
        prompt = f"""
        Tu tarea es analizar la siguiente transcripción de un video de YouTube y crear 5-7 taglines concisas que resuman los puntos principales.
        Cada tagline debe ser breve (5-10 palabras), impactante y capturar una idea clave o momento importante.
        
        Transcripción:
        {text}
        
        Formato de salida:
        - Tagline 1: [Punto clave 1]
        - Tagline 2: [Punto clave 2]
        ...
        
        Tu resumen debe capturar la esencia del contenido de manera breve y memorable.
        """
        
        logging.info("Generando resumen con Claude 3.7...")
        
        # Llamar a la API de Claude
        response = client.messages.create(
            model="claude-3-7-sonnet-20240620",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        summary = response.content[0].text
        
        # Generar nombre de archivo único basado en la primera parte del texto
        first_words = text.split()[:3]
        file_name = "_".join(first_words)[:30] + "_summary.txt"
        output_path = os.path.join(output_dir, file_name)
        
        # Guardar resumen en archivo
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary)
            
        logging.info(f"Resumen guardado en: {output_path}")
        
        return output_path, summary
        
    except Exception as e:
        logging.error(f"Error al resumir texto: {str(e)}")
        raise

def summarize_multiple(transcription_results, output_dir='summaries', api_key=None):
    """
    Resumir múltiples transcripciones
    
    Args:
        transcription_results (list): Lista de resultados de transcripción
        output_dir (str): Directorio donde se guardarán los resúmenes
        api_key (str): API key de Anthropic
        
    Returns:
        list: Lista de diccionarios con información de los resúmenes
    """
    results = []
    
    for item in transcription_results:
        try:
            transcription_text = item['transcription_text']
            audio_file = item['audio_file']
            
            # Obtener nombre base del archivo de audio
            base_name = os.path.basename(audio_file)
            file_name = os.path.splitext(base_name)[0]
            
            # Crear nombre específico para el archivo de resumen
            summary_path = os.path.join(output_dir, f"{file_name}_summary.txt")
            
            # Resumir texto
            _, summary = summarize_text(transcription_text, output_dir, api_key)
            
            results.append({
                'original_file': audio_file,
                'transcription_file': item['transcription_file'],
                'summary_file': summary_path,
                'summary_text': summary
            })
            
        except Exception as e:
            logging.error(f"Error al resumir {item.get('audio_file', 'desconocido')}: {str(e)}")
    
    return results 