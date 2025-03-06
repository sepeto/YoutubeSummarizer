import os
import time
import logging
from datetime import datetime
from anthropic import Anthropic
from openai import OpenAI
from src import config
from src.utils import CacheManager

class BaseSummarizer:
    def __init__(self, api_key=None, output_dir=None):
        self.output_dir = output_dir or config.SUMMARY_DIR
        self.last_request_time = 0
        self._setup_logging()
        self._ensure_output_dir()
        
    def _setup_logging(self):
        """Configurar logging específico para el summarizer"""
        self.logger = logging.getLogger('summarizer')
        self.logger.setLevel(logging.INFO)
        
        # Crear el directorio de logs si no existe
        log_dir = config.LOG_DIR
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Handler para archivo
        log_file = os.path.join(log_dir, f'summarize_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        self.logger.addHandler(console_handler)
        
    def _ensure_output_dir(self):
        """Asegurar que existe el directorio de salida"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.logger.info(f"Directorio de resúmenes creado: {self.output_dir}")
    
    def _apply_rate_limiting(self, rate_limit):
        """Aplicar rate limiting si está habilitado"""
        if config.ENABLE_RATE_LIMITING:
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            wait_time = (60.0 / rate_limit) - time_since_last_request
            
            if wait_time > 0:
                self.logger.info(f"Rate limiting: esperando {wait_time:.2f} segundos antes de la siguiente llamada API")
                time.sleep(wait_time)
    
    def summarize_multiple(self, transcription_results):
        """
        Resumir múltiples transcripciones
        
        Args:
            transcription_results (list): Lista de resultados de transcripción
            
        Returns:
            list: Lista de diccionarios con información de los resúmenes
        """
        results = []
        failed_files = []
        
        total_files = len(transcription_results)
        self.logger.info(f"Procesando {total_files} transcripciones")
        
        for i, item in enumerate(transcription_results, 1):
            try:
                self.logger.info(f"\nProcesando transcripción {i}/{total_files}")
                
                # Obtener información del archivo original
                audio_file = item['audio_file']
                transcription_text = item['transcription_text']
                base_name = os.path.splitext(os.path.basename(audio_file))[0]
                
                # Generar resumen
                summary_path, summary = self.summarize_text(transcription_text, base_name)
                
                results.append({
                    'original_file': audio_file,
                    'transcription_file': item['transcription_file'],
                    'summary_file': summary_path,
                    'summary_text': summary
                })
                
                self.logger.info(f"Transcripción {i}/{total_files} procesada correctamente")
                
            except Exception as e:
                self.logger.error(f"Error al procesar transcripción {i}/{total_files}: {str(e)}")
                failed_files.append(item.get('audio_file', 'desconocido'))
                
        # Resumen final
        success_count = len(results)
        failed_count = len(failed_files)
        
        self.logger.info("\n=== RESUMEN DE PROCESAMIENTO ===")
        self.logger.info(f"Total transcripciones procesadas: {total_files}")
        self.logger.info(f"Resúmenes exitosos: {success_count}")
        self.logger.info(f"Resúmenes fallidos: {failed_count}")
        
        if failed_files:
            self.logger.warning("\nArchivos que fallaron:")
            for file in failed_files:
                self.logger.warning(f"- {file}")
                
        return results

class ClaudeSummarizer(BaseSummarizer):
    def __init__(self, api_key=None, output_dir=None):
        super().__init__(output_dir=output_dir)
        self.api_key = api_key or config.ANTHROPIC_API_KEY
        self.model = config.CLAUDE_MODEL
        self.client = None
            
    def _init_client(self):
        """Inicializar cliente de Anthropic"""
        if not self.api_key:
            raise ValueError("Se requiere API key de Anthropic")
            
        if self.client is None:
            self.client = Anthropic(api_key=self.api_key)
            
    def summarize_text(self, text, source_name):
        """
        Resumir texto usando Claude con reintentos y rate limiting
        
        Args:
            text (str): Texto a resumir
            source_name (str): Nombre del archivo fuente para nombrar el resumen
            
        Returns:
            tuple: (ruta_resumen, texto_resumen)
        """
        self.logger.info(f"Iniciando resumen para: {source_name}")
        
        # Verificar caché si está habilitado
        if config.ENABLE_CACHE:
            cache_key = f"{source_name}_claude"
            cached_result = CacheManager.get_cache(cache_key, "summary")
            if cached_result:
                self.logger.info(f"Usando resumen en caché para: {source_name}")
                return cached_result["file_path"], cached_result["text"]
        
        # Construir prompt
        prompt = f"""
        Analiza la siguiente transcripción de un video de YouTube y crea 5-7 taglines concisas que resuman los puntos principales.
        Cada tagline debe ser breve (5-10 palabras), impactante y capturar una idea clave o momento importante.
        
        Transcripción:
        {text}
        
        Formato de salida:
        - Tagline 1: [Punto clave 1]
        - Tagline 2: [Punto clave 2]
        ...
        
        El resumen debe capturar la esencia del contenido de manera breve y memorable.
        """
        
        # Realizar resumen con reintentos
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                self.logger.info(f"Intento de resumen {attempt}/{config.MAX_RETRIES}")
                self._init_client()
                
                # Aplicar rate limiting
                self._apply_rate_limiting(config.ANTHROPIC_RATE_LIMIT)
                
                # Llamar a la API
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                self.last_request_time = time.time()
                summary = response.content[0].text
                
                # Guardar resumen
                output_path = os.path.join(self.output_dir, f"{source_name}_summary.txt")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(summary)
                    
                self.logger.info(f"Resumen guardado en: {output_path}")
                
                # Guardar en caché si está habilitado
                if config.ENABLE_CACHE:
                    CacheManager.save_cache(cache_key, "summary", {
                        "file_path": output_path,
                        "text": summary
                    })
                
                return output_path, summary
                
            except Exception as e:
                self.logger.error(f"Error en intento {attempt}: {str(e)}")
                if attempt < config.MAX_RETRIES:
                    wait_time = config.RETRY_DELAY * attempt
                    self.logger.info(f"Reintentando en {wait_time} segundos...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Todos los intentos de resumen fallaron para {source_name}")
                    raise

class OpenAISummarizer(BaseSummarizer):
    def __init__(self, api_key=None, output_dir=None):
        super().__init__(output_dir=output_dir)
        self.api_key = api_key or config.OPENAI_API_KEY
        self.model = config.OPENAI_MODEL
        self.client = None
            
    def _init_client(self):
        """Inicializar cliente de OpenAI"""
        if not self.api_key:
            raise ValueError("Se requiere API key de OpenAI")
            
        if self.client is None:
            self.client = OpenAI(api_key=self.api_key)
            
    def summarize_text(self, text, source_name):
        """
        Resumir texto usando OpenAI con reintentos y rate limiting
        
        Args:
            text (str): Texto a resumir
            source_name (str): Nombre del archivo fuente para nombrar el resumen
            
        Returns:
            tuple: (ruta_resumen, texto_resumen)
        """
        self.logger.info(f"Iniciando resumen para: {source_name}")
        
        # Verificar caché si está habilitado
        if config.ENABLE_CACHE:
            cache_key = f"{source_name}_openai"
            cached_result = CacheManager.get_cache(cache_key, "summary")
            if cached_result:
                self.logger.info(f"Usando resumen en caché para: {source_name}")
                return cached_result["file_path"], cached_result["text"]
        
        # Construir prompt
        prompt = f"""
        Analiza la siguiente transcripción de un video de YouTube y crea 5-7 taglines concisas que resuman los puntos principales.
        Cada tagline debe ser breve (5-10 palabras), impactante y capturar una idea clave o momento importante.
        
        Transcripción:
        {text}
        
        Formato de salida:
        - Tagline 1: [Punto clave 1]
        - Tagline 2: [Punto clave 2]
        ...
        
        El resumen debe capturar la esencia del contenido de manera breve y memorable.
        """
        
        # Realizar resumen con reintentos
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                self.logger.info(f"Intento de resumen {attempt}/{config.MAX_RETRIES}")
                self._init_client()
                
                # Aplicar rate limiting
                self._apply_rate_limiting(config.OPENAI_RATE_LIMIT)
                
                # Llamar a la API
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Eres un experto en resumir contenido. Genera taglines concisas y memorables."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                self.last_request_time = time.time()
                summary = response.choices[0].message.content
                
                # Guardar resumen
                output_path = os.path.join(self.output_dir, f"{source_name}_summary.txt")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(summary)
                    
                self.logger.info(f"Resumen guardado en: {output_path}")
                
                # Guardar en caché si está habilitado
                if config.ENABLE_CACHE:
                    CacheManager.save_cache(cache_key, "summary", {
                        "file_path": output_path,
                        "text": summary
                    })
                
                return output_path, summary
                
            except Exception as e:
                self.logger.error(f"Error en intento {attempt}: {str(e)}")
                if attempt < config.MAX_RETRIES:
                    wait_time = config.RETRY_DELAY * attempt
                    self.logger.info(f"Reintentando en {wait_time} segundos...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Todos los intentos de resumen fallaron para {source_name}")
                    raise

def get_summarizer():
    """Factory function para obtener el summarizer configurado"""
    if config.SUMMARIZATION_METHOD == "openai":
        return OpenAISummarizer()
    elif config.SUMMARIZATION_METHOD == "claude":
        return ClaudeSummarizer()
    else:
        raise ValueError(f"Método de resumen no soportado: {config.SUMMARIZATION_METHOD}")