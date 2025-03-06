"""
Models for transcription and summarization with improved error handling and retries
"""
import os
import time
import logging
from openai import OpenAI
from anthropic import Anthropic
from . import config
import openai
import sys

logger = logging.getLogger(__name__)

class Transcriber:
    @staticmethod
    def get_transcriber():
        """
        Factory method para obtener el transcriptor adecuado según la configuración.
        Incluye verificación de disponibilidad de API keys y fallback a métodos locales.
        """
        # Verificar si el método configurado es viable
        if config.TRANSCRIPTION_METHOD == "api" and not config.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY no está configurada. Cambiando a transcripción local.")
            print("[ADVERTENCIA] OPENAI_API_KEY no está configurada. Cambiando a transcripción local.")
            config.TRANSCRIPTION_METHOD = "local"
            
        # Verificar dependencias para transcripción local
        if config.TRANSCRIPTION_METHOD == "local":
            try:
                import whisper
            except ImportError:
                logger.error("No se pudo importar el módulo 'whisper'. Instálelo con: pip install openai-whisper")
                print("[ERROR] No se pudo importar el módulo 'whisper'. Instálelo con: pip install openai-whisper")
                print("[INFO] Intentando usar la API de OpenAI como alternativa...")
                
                if config.OPENAI_API_KEY:
                    config.TRANSCRIPTION_METHOD = "api"
                else:
                    logger.error("No hay métodos de transcripción disponibles. Verifique la instalación y las claves API.")
                    print("[ERROR] No hay métodos de transcripción disponibles. Verifique la instalación y las claves API.")
        
        # Crear el transcriptor según el método configurado
        if config.TRANSCRIPTION_METHOD == "local":
            return LocalWhisperTranscriber()
        elif config.TRANSCRIPTION_METHOD == "api":
            return APIWhisperTranscriber()
        else:
            raise ValueError(f"Método de transcripción no válido: {config.TRANSCRIPTION_METHOD}")

class LocalWhisperTranscriber:
    def __init__(self):
        try:
            import whisper
            self.model = None
            self.model_size = config.WHISPER_MODEL
            logger.info(f"Transcriptor local inicializado con modelo {self.model_size}")
        except ImportError:
            logger.error("No se pudo importar el módulo 'whisper'. Instálelo con: pip install openai-whisper")
            print("[ERROR] No se pudo importar el módulo 'whisper'. Instálelo con: pip install openai-whisper")
            raise
    
    def _load_model(self):
        """Lazy load the model only when needed"""
        if self.model is None:
            try:
                import whisper
                logger.info(f"Cargando modelo Whisper: {self.model_size}")
                print(f"[INFO] Cargando modelo Whisper: {self.model_size}")
                self.model = whisper.load_model(self.model_size)
            except Exception as e:
                logger.error(f"Error cargando modelo Whisper: {str(e)}")
                print(f"[ERROR] Error cargando modelo Whisper: {str(e)}")
                raise
    
    def transcribe(self, audio_file):
        """Transcribir audio usando el modelo local de Whisper con reintentos"""
        if not os.path.exists(audio_file):
            error_msg = f"El archivo de audio no existe: {audio_file}"
            logger.error(error_msg)
            print(f"[ERROR] {error_msg}")
            raise FileNotFoundError(error_msg)
            
        self._load_model()
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                logger.info(f"Intento de transcripción {attempt}/{config.MAX_RETRIES} para {audio_file}")
                print(f"[INFO] Intento de transcripción {attempt}/{config.MAX_RETRIES} para {audio_file}")
                result = self.model.transcribe(audio_file)
                return result["text"]
            except Exception as e:
                logger.error(f"Error en intento de transcripción {attempt}: {str(e)}")
                print(f"[ERROR] Error en intento de transcripción {attempt}: {str(e)}")
                if attempt < config.MAX_RETRIES:
                    wait_time = config.RETRY_DELAY * attempt
                    logger.info(f"Reintentando en {wait_time} segundos...")
                    print(f"[INFO] Reintentando en {wait_time} segundos...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Todos los intentos de transcripción fallaron para {audio_file}")
                    print(f"[ERROR] Todos los intentos de transcripción fallaron para {audio_file}")
                    raise

class APIWhisperTranscriber:
    def __init__(self):
        """Inicializar el transcriptor de API con verificación de clave API"""
        if not config.OPENAI_API_KEY:
            error_msg = "OPENAI_API_KEY no está configurada. No se puede usar la API de OpenAI para transcripción."
            logger.error(error_msg)
            print(f"[ERROR] {error_msg}")
            raise ValueError(error_msg)
            
        try:
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.last_request_time = 0
            logger.info("Transcriptor de API inicializado correctamente")
        except Exception as e:
            logger.error(f"Error inicializando cliente de OpenAI: {str(e)}")
            print(f"[ERROR] Error inicializando cliente de OpenAI: {str(e)}")
            raise
    
    def transcribe(self, audio_file):
        """Transcribir audio usando la API de Whisper con reintentos y rate limiting"""
        if not os.path.exists(audio_file):
            error_msg = f"El archivo de audio no existe: {audio_file}"
            logger.error(error_msg)
            print(f"[ERROR] {error_msg}")
            raise FileNotFoundError(error_msg)
            
        # Verificar tamaño del archivo (límite de 25MB para la API)
        file_size_mb = os.path.getsize(audio_file) / (1024 * 1024)
        if file_size_mb > 25:
            error_msg = f"El archivo es demasiado grande para la API de Whisper ({file_size_mb:.2f}MB > 25MB)"
            logger.error(error_msg)
            print(f"[ERROR] {error_msg}")
            print("[INFO] Intente usar la transcripción local para archivos grandes")
            raise ValueError(error_msg)
            
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                # Implement rate limiting if enabled
                if config.ENABLE_RATE_LIMITING:
                    current_time = time.time()
                    time_since_last_request = current_time - self.last_request_time
                    wait_time = (60.0 / config.OPENAI_RATE_LIMIT) - time_since_last_request
                    
                    if wait_time > 0:
                        logger.info(f"Rate limiting: esperando {wait_time:.2f} segundos antes de la siguiente llamada a la API")
                        print(f"[INFO] Rate limiting: esperando {wait_time:.2f} segundos...")
                        time.sleep(wait_time)
                
                logger.info(f"Intento de transcripción {attempt}/{config.MAX_RETRIES} para {audio_file}")
                print(f"[INFO] Intento de transcripción {attempt}/{config.MAX_RETRIES} para {audio_file}")
                
                with open(audio_file, "rb") as f:
                    result = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f
                    )
                
                self.last_request_time = time.time()
                return result.text
                
            except Exception as e:
                logger.error(f"Error en intento de transcripción {attempt}: {str(e)}")
                print(f"[ERROR] Error en intento de transcripción {attempt}: {str(e)}")
                
                # Detectar errores específicos de la API
                error_str = str(e).lower()
                if "api key" in error_str or "authentication" in error_str:
                    logger.error("Error de autenticación con la API de OpenAI. Verifique su clave API.")
                    print("[ERROR] Error de autenticación con la API de OpenAI. Verifique su clave API.")
                    raise
                elif "rate limit" in error_str:
                    wait_time = config.RETRY_DELAY * 2 * attempt  # Esperar más tiempo en caso de rate limit
                    logger.warning(f"Rate limit alcanzado. Esperando {wait_time} segundos...")
                    print(f"[ADVERTENCIA] Rate limit alcanzado. Esperando {wait_time} segundos...")
                    time.sleep(wait_time)
                
                if attempt < config.MAX_RETRIES:
                    wait_time = config.RETRY_DELAY * attempt
                    logger.info(f"Reintentando en {wait_time} segundos...")
                    print(f"[INFO] Reintentando en {wait_time} segundos...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Todos los intentos de transcripción fallaron para {audio_file}")
                    print(f"[ERROR] Todos los intentos de transcripción fallaron para {audio_file}")
                    raise

class Summarizer:
    @staticmethod
    def get_summarizer():
        if config.SUMMARIZATION_METHOD == "openai":
            return OpenAISummarizer()
        elif config.SUMMARIZATION_METHOD == "claude":
            return ClaudeSummarizer()
        elif config.SUMMARIZATION_METHOD == "llama":
            raise NotImplementedError("Llama summarizer not available")
        elif config.SUMMARIZATION_METHOD == "gpt4allmini":
            raise NotImplementedError("GPT4All summarizer not available")
        else:
            raise ValueError(f"Invalid summarization method: {config.SUMMARIZATION_METHOD}")

class OpenAISummarizer(Summarizer):
    def __init__(self):
        super().__init__()
        self.model = config.OPENAI_MODEL
        self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        self.last_request_time = 0
        
    def summarize(self, text):
        """Generar resumen usando OpenAI con reintentos y rate limiting"""
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                # Implement rate limiting if enabled
                if config.ENABLE_RATE_LIMITING:
                    current_time = time.time()
                    time_since_last_request = current_time - self.last_request_time
                    wait_time = (60.0 / config.OPENAI_RATE_LIMIT) - time_since_last_request
                    
                    if wait_time > 0:
                        logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds before next API call")
                        time.sleep(wait_time)
                
                logger.info(f"Summarization attempt {attempt}/{config.MAX_RETRIES} using OpenAI")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Eres un experto en resumir contenido. Genera un resumen detallado y bien estructurado del texto proporcionado."},
                        {"role": "user", "content": f"Resume el siguiente texto:\n\n{text}"}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                self.last_request_time = time.time()
                return response.choices[0].message.content
                
            except Exception as e:
                logger.error(f"Error in summarization attempt {attempt}: {str(e)}")
                if attempt < config.MAX_RETRIES:
                    wait_time = config.RETRY_DELAY * attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All summarization attempts failed")
                    raise
            
    def translate(self, text, target_lang='es'):
        """Traducir texto usando OpenAI con reintentos y rate limiting"""
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                # Implement rate limiting if enabled
                if config.ENABLE_RATE_LIMITING:
                    current_time = time.time()
                    time_since_last_request = current_time - self.last_request_time
                    wait_time = (60.0 / config.OPENAI_RATE_LIMIT) - time_since_last_request
                    
                    if wait_time > 0:
                        logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds before next API call")
                        time.sleep(wait_time)
                
                lang_name = "español" if target_lang == 'es' else "inglés"
                logger.info(f"Translation attempt {attempt}/{config.MAX_RETRIES} to {lang_name}")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": f"Eres un experto traductor. Traduce el texto al {lang_name} manteniendo el significado y el tono original."},
                        {"role": "user", "content": f"Traduce el siguiente texto al {lang_name}:\n\n{text}"}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
                
                self.last_request_time = time.time()
                return response.choices[0].message.content
                
            except Exception as e:
                logger.error(f"Error in translation attempt {attempt}: {str(e)}")
                if attempt < config.MAX_RETRIES:
                    wait_time = config.RETRY_DELAY * attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All translation attempts failed")
                    raise

class ClaudeSummarizer(Summarizer):
    def __init__(self):
        super().__init__()
        self.model = config.CLAUDE_MODEL
        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.last_request_time = 0
        
    def summarize(self, text):
        """Generar resumen usando Claude con reintentos y rate limiting"""
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                # Implement rate limiting if enabled
                if config.ENABLE_RATE_LIMITING:
                    current_time = time.time()
                    time_since_last_request = current_time - self.last_request_time
                    wait_time = (60.0 / config.ANTHROPIC_RATE_LIMIT) - time_since_last_request
                    
                    if wait_time > 0:
                        logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds before next API call")
                        time.sleep(wait_time)
                
                logger.info(f"Summarization attempt {attempt}/{config.MAX_RETRIES} using Claude")
                
                # Construir prompt
                prompt = f"""
                Analiza la siguiente transcripción de un video de YouTube y crea un resumen detallado y bien estructurado.
                
                Transcripción:
                {text}
                
                El resumen debe capturar la esencia del contenido de manera clara y concisa.
                """
                
                # Llamar a la API
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                self.last_request_time = time.time()
                return response.content[0].text
                
            except Exception as e:
                logger.error(f"Error in summarization attempt {attempt}: {str(e)}")
                if attempt < config.MAX_RETRIES:
                    wait_time = config.RETRY_DELAY * attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All summarization attempts failed")
                    raise
    
    def translate(self, text, target_lang='es'):
        """Traducir texto usando Claude con reintentos y rate limiting"""
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                # Implement rate limiting if enabled
                if config.ENABLE_RATE_LIMITING:
                    current_time = time.time()
                    time_since_last_request = current_time - self.last_request_time
                    wait_time = (60.0 / config.ANTHROPIC_RATE_LIMIT) - time_since_last_request
                    
                    if wait_time > 0:
                        logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds before next API call")
                        time.sleep(wait_time)
                
                lang_name = "español" if target_lang == 'es' else "inglés"
                logger.info(f"Translation attempt {attempt}/{config.MAX_RETRIES} to {lang_name}")
                
                # Construir prompt
                prompt = f"""
                Traduce el siguiente texto al {lang_name} manteniendo el significado y el tono original.
                
                Texto original:
                {text}
                """
                
                # Llamar a la API
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                self.last_request_time = time.time()
                return response.content[0].text
                
            except Exception as e:
                logger.error(f"Error in translation attempt {attempt}: {str(e)}")
                if attempt < config.MAX_RETRIES:
                    wait_time = config.RETRY_DELAY * attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All translation attempts failed")
                    raise

class RecommendationGenerator:
    """
    Clase para generar recomendaciones de depuración y refactorización
    basadas en los logs de ejecución utilizando GPT-3.5-Turbo (GPT-01-mini)
    """
    def __init__(self):
        """Inicializar el generador de recomendaciones con verificación de clave API"""
        if not config.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY no está configurada. No se pueden generar recomendaciones.")
            print("[ERROR] OPENAI_API_KEY no está configurada. No se pueden generar recomendaciones.")
            self.available = False
            return
            
        try:
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.available = True
            logger.info("Generador de recomendaciones inicializado correctamente")
        except Exception as e:
            logger.error(f"Error inicializando cliente de OpenAI para recomendaciones: {str(e)}")
            print(f"[ERROR] Error inicializando cliente de OpenAI para recomendaciones: {str(e)}")
            self.available = False
    
    def generate_recommendations(self, log_content, output_file):
        """
        Genera recomendaciones de depuración y refactorización basadas en los logs
        
        Args:
            log_content (str): Contenido de los logs de ejecución
            output_file (str): Ruta del archivo donde guardar las recomendaciones
        
        Returns:
            bool: True si las recomendaciones se generaron correctamente, False en caso contrario
        """
        if not self.available:
            logger.error("No se pueden generar recomendaciones: generador no disponible")
            print("[ERROR] No se pueden generar recomendaciones: generador no disponible")
            return False
            
        try:
            logger.info("Generando recomendaciones basadas en logs...")
            print("[INFO] Generando recomendaciones basadas en logs...")
            
            # Preparar el prompt para el modelo
            prompt = f"""
            Analiza los siguientes logs de ejecución de un programa de descarga y transcripción de videos de YouTube.
            Identifica problemas, errores y posibles mejoras. Genera recomendaciones de depuración y refactorización
            para resolver los problemas encontrados. Organiza tu respuesta en secciones:
            
            1. Resumen de problemas detectados
            2. Recomendaciones de depuración
            3. Recomendaciones de refactorización
            4. Sugerencias de mejora
            
            LOGS:
            {log_content}
            """
            
            # Limitar el tamaño del prompt si es demasiado grande
            max_tokens = 4000  # Aproximadamente 16K caracteres
            if len(prompt) > max_tokens * 4:
                logger.warning(f"Logs demasiado grandes ({len(prompt)} caracteres), truncando...")
                print(f"[ADVERTENCIA] Logs demasiado grandes ({len(prompt)} caracteres), truncando...")
                prompt = prompt[:max_tokens * 4]
            
            # Llamar a la API de OpenAI
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Equivalente a GPT-01-mini
                messages=[
                    {"role": "system", "content": "Eres un experto en Python y desarrollo de software especializado en depuración y refactorización de código."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            recommendations = response.choices[0].message.content
            
            # Guardar las recomendaciones en un archivo
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# Recomendaciones de Depuración y Refactorización\n")
                f.write(f"# Generado el: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(recommendations)
            
            logger.info(f"Recomendaciones guardadas en: {output_file}")
            print(f"[INFO] Recomendaciones guardadas en: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error generando recomendaciones: {str(e)}")
            print(f"[ERROR] Error generando recomendaciones: {str(e)}")
            return False
    
    def generate_from_log_file(self, log_file_path, output_file=None):
        """
        Genera recomendaciones basadas en un archivo de log
        
        Args:
            log_file_path (str): Ruta al archivo de log
            output_file (str, optional): Ruta donde guardar las recomendaciones.
                                        Si es None, se usará el mismo nombre del log con sufijo '_recommendations.md'
        
        Returns:
            bool: True si las recomendaciones se generaron correctamente, False en caso contrario
        """
        if not os.path.exists(log_file_path):
            logger.error(f"Archivo de log no encontrado: {log_file_path}")
            print(f"[ERROR] Archivo de log no encontrado: {log_file_path}")
            return False
            
        try:
            # Leer el archivo de log
            with open(log_file_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            # Determinar el nombre del archivo de salida si no se especificó
            if output_file is None:
                base_name = os.path.splitext(log_file_path)[0]
                output_file = f"{base_name}_recommendations.md"
            
            # Generar las recomendaciones
            return self.generate_recommendations(log_content, output_file)
            
        except Exception as e:
            logger.error(f"Error procesando archivo de log: {str(e)}")
            print(f"[ERROR] Error procesando archivo de log: {str(e)}")
            return False