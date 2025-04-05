import os
import openai
import logging
from typing import List

# Configurar el logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurar la API key de OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

class Summarizer:
    def __init__(self, max_tokens_per_chunk=3000):
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.prompt = "Por favor, resume el siguiente texto manteniendo los puntos más importantes y el contexto general:"
        self.combine_prompt = "Por favor, combina los siguientes resúmenes en un único resumen coherente:"

    def _split_text(self, text: str) -> List[str]:
        """Divide el texto en chunks más pequeños basados en el número de tokens"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_token_count = 0
        
        # Estimación aproximada: 1 palabra = 1.3 tokens en promedio
        words_per_chunk = int(self.max_tokens_per_chunk / 1.3)
        
        for word in words:
            current_chunk.append(word)
            current_token_count += 1
            
            if current_token_count >= words_per_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_token_count = 0
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks

    def generate_summary(self, text: str) -> str:
        try:
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=f"{self.prompt}\n\n{text}",
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].text.strip()
        except Exception as e:
            logger.error(f"Error al generar el resumen: {str(e)}")
            raise

    def combine_summaries(self, summaries: List[str]) -> str:
        try:
            combined_text = "\n\n".join(summaries)
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=f"{self.combine_prompt}\n\n{combined_text}",
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].text.strip()
        except Exception as e:
            logger.error(f"Error al combinar los resúmenes: {str(e)}")
            raise

def summarize_files():
    logger.info("Iniciando proceso de resumen...")
    
    # Crear directorio de resúmenes si no existe
    os.makedirs("Resumenes", exist_ok=True)
    
    summarizer = Summarizer()
    
    # Procesar cada archivo en el directorio de transcripciones
    for filename in os.listdir("Transcripciones"):
        if filename.endswith(".txt"):
            logger.info(f"\nProcesando: {filename}")
            
            # Leer el archivo
            input_path = os.path.join("Transcripciones", filename)
            output_path = os.path.join("Resumenes", filename)
            
            try:
                with open(input_path, "r", encoding="utf-8") as f:
                    text = f.read()
                
                # Dividir el texto en chunks si es necesario
                chunks = summarizer._split_text(text)
                logger.info(f"Texto dividido en {len(chunks)} partes")
                
                # Generar resúmenes para cada chunk
                summaries = []
                for i, chunk in enumerate(chunks, 1):
                    logger.info(f"Procesando parte {i}/{len(chunks)}...")
                    try:
                        summary = summarizer.generate_summary(chunk)
                        summaries.append(summary)
                    except Exception as e:
                        logger.error(f"Error al generar el resumen para la parte {i}: {str(e)}")
                        raise
                
                # Combinar los resúmenes si hay múltiples chunks
                final_summary = (
                    summarizer.combine_summaries(summaries)
                    if len(summaries) > 1
                    else summaries[0]
                )
                
                # Guardar el resumen
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(final_summary)
                
                logger.info(f"Resumen guardado en: {output_path}")
                
            except Exception as e:
                logger.error(f"No se pudo generar el resumen para: {filename}")
                logger.error(str(e))
                continue
    
    logger.info("\nProceso completado!")

if __name__ == "__main__":
    summarize_files() 