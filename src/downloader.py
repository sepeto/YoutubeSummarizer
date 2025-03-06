import os
import yt_dlp
import logging
import re
from datetime import datetime
from . import config
from .models import Transcriber, Summarizer, OpenAISummarizer, RecommendationGenerator
import sys
import tempfile

class YouTubeDownloader:
    def __init__(self, base_dir='output'):
        self.base_dir = base_dir
        self.output_dir = os.path.join(base_dir, 'downloads')
        self.transcriptions_dir = os.path.join(base_dir, 'transcriptions')
        self.summaries_dir = os.path.join(base_dir, 'summaries')
        self.log_dir = os.path.join(base_dir, 'logs')
        self.usage_log_dir = os.path.join(base_dir, 'usage_logs')
        self.checkpoint_file = os.path.join(base_dir, 'checkpoint.txt')
        
        # Primero configurar el logging
        self._setup_logging()
        
        # Luego asegurar que existan los directorios
        self._ensure_directories()
        
        # Después actualizar dependencias
        self._update_dependencies()
        
        self.transcriber = Transcriber.get_transcriber()
        self.summarizer = Summarizer.get_summarizer()
        self.usage_data = {
            'whisper': {'seconds': 0, 'cost_per_minute': 0.006},  # $0.006 per minute
            'gpt-3.5-turbo': {'input_tokens': 0, 'output_tokens': 0, 'cost_per_1k_input': 0.0015, 'cost_per_1k_output': 0.002},  # $0.0015/1K input, $0.002/1K output
            'gpt-4': {'input_tokens': 0, 'output_tokens': 0, 'cost_per_1k_input': 0.03, 'cost_per_1k_output': 0.06}  # $0.03/1K input, $0.06/1K output
        }
        
    def _setup_logging(self):
        """Configurar logging específico para el downloader"""
        self.logger = logging.getLogger('downloader')
        self.logger.setLevel(logging.DEBUG)  # Cambiar a DEBUG para más detalle
        
        # Configurar codificación por defecto para sys.stdout
        if sys.stdout.encoding != 'utf-8':
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
            
        # Limpiar handlers existentes
        self.logger.handlers = []
        
        try:
            # Handler para archivo con encoding UTF-8
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(self.log_dir, f'process_{timestamp}.log')
            file_handler = logging.FileHandler(log_file, encoding='utf-8', errors='replace')
            file_format = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s\nDetalles: %(pathname)s:%(lineno)d\n')
            file_handler.setFormatter(file_format)
            file_handler.setLevel(logging.DEBUG)  # Capturar todo en el archivo
            self.logger.addHandler(file_handler)
            
            # Handler para consola con encoding UTF-8
            console_handler = logging.StreamHandler(sys.stdout)
            console_format = logging.Formatter('[%(levelname)s] %(message)s')
            console_handler.setFormatter(console_format)
            console_handler.setLevel(logging.INFO)  # Solo INFO y superior en consola
            self.logger.addHandler(console_handler)
            
            # Añadir filtros para categorizar mensajes
            class ErrorFilter(logging.Filter):
                def filter(self, record):
                    if record.levelno >= logging.ERROR:
                        record.category = "ERROR"
                    elif record.levelno >= logging.WARNING:
                        record.category = "WARNING"
                    elif record.levelno >= logging.INFO:
                        record.category = "INFO"
                    else:
                        record.category = "DEBUG"
                    return True
            
            self.logger.addFilter(ErrorFilter())
            
        except Exception as e:
            print(f"[ERROR] Error configurando logging: {str(e)}")
            
    def _sanitize_text(self, text):
        """Eliminar caracteres problemáticos del texto manteniendo caracteres especiales válidos"""
        try:
            # Convertir a string si no lo es
            text = str(text)
            
            # Eliminar caracteres de control y no imprimibles
            text = ''.join(char for char in text if char.isprintable() or char in ['\n', '\t', ' '])
            
            # Reemplazar caracteres no permitidos en nombres de archivo
            text = re.sub(r'[<>:"/\\|?*]', '_', text)
            
            # Eliminar espacios múltiples
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
        except Exception:
            return str(text)
            
    def _ensure_directories(self):
        """Asegurar que existen todos los directorios necesarios"""
        for dir_path in [self.output_dir, self.transcriptions_dir, self.summaries_dir, self.log_dir, self.usage_log_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                self.logger.info(f"Directorio creado: {dir_path}")

    def _update_dependencies(self):
        """Actualizar las librerías de descarga de YouTube"""
        try:
            import subprocess
            self._log_info("Iniciando actualización de librerías de descarga...")
            
            # Solo las librerías de descarga
            dependencies = [
                "yt-dlp",
                "pytube",
                "youtube-dl"
            ]
            
            for dep in dependencies:
                try:
                    self._log_info(f"Actualizando {dep}...")
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "--upgrade", dep],
                        capture_output=True,
                        text=True,
                        encoding='utf-8'
                    )
                    
                    if result.returncode == 0:
                        self._log_info(f"{dep} actualizado correctamente")
                    else:
                        self._log_warning(f"Error actualizando {dep}: {result.stderr}")
                except Exception as e:
                    self._log_error(f"Error actualizando {dep}", e)
            
            self._log_info("Proceso de actualización completado")
        except Exception as e:
            self._log_error("Error en el proceso de actualización", e)

    def _log_error(self, message, error, context=None):
        """Registrar error con contexto detallado"""
        error_details = {
            'message': message,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'timestamp': datetime.now().isoformat()
        }
        
        # Verificar si el logger ya está inicializado
        if hasattr(self, 'logger'):
            self.logger.error(f"{message}\nError: {error}\nTipo: {type(error).__name__}")
            if context:
                self.logger.error(f"Contexto: {context}")
                
            # Guardar error en archivo separado
            try:
                error_file = os.path.join(self.log_dir, f'errors_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                import json
                with open(error_file, 'w', encoding='utf-8') as f:
                    json.dump(error_details, f, indent=2, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"Error guardando detalles del error: {str(e)}")
        else:
            # Si el logger no está inicializado, imprimir en consola
            print(f"[ERROR] {message}\nError: {error}\nTipo: {type(error).__name__}")
            if context:
                print(f"[ERROR] Contexto: {context}")
            
    def _log_warning(self, message, details=None):
        """Registrar advertencia con detalles"""
        warning_details = {
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        # Verificar si el logger ya está inicializado
        if hasattr(self, 'logger'):
            self.logger.warning(f"{message}")
            if details:
                self.logger.warning(f"Detalles: {details}")
                
            # Guardar advertencia en archivo separado
            try:
                warning_file = os.path.join(self.log_dir, f'warnings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                import json
                with open(warning_file, 'w', encoding='utf-8') as f:
                    json.dump(warning_details, f, indent=2, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"Error guardando detalles de la advertencia: {str(e)}")
        else:
            # Si el logger no está inicializado, imprimir en consola
            print(f"[WARNING] {message}")
            if details:
                print(f"[WARNING] Detalles: {details}")
            
    def _log_info(self, message, details=None):
        """Registrar información con detalles"""
        info_details = {
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        # Verificar si el logger ya está inicializado
        if hasattr(self, 'logger'):
            self.logger.info(f"{message}")
            if details:
                self.logger.info(f"Detalles: {details}")
                
            # Guardar información en archivo separado
            try:
                info_file = os.path.join(self.log_dir, f'info_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                import json
                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump(info_details, f, indent=2, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"Error guardando detalles de la información: {str(e)}")
        else:
            # Si el logger no está inicializado, imprimir en consola
            print(f"[INFO] {message}")
            if details:
                print(f"[INFO] Detalles: {details}")

    def download_video(self, url):
        """Descargar un video de YouTube usando múltiples métodos"""
        self.logger.info(f"Iniciando descarga para: {url}")
        print(f"[INFO] Iniciando descarga para: {url}")
        
        # Obtener título del video
        title = self._get_video_title(url)
        self.logger.info(f"Título del video: {title}")
        print(f"[INFO] Título del video: {title}")
        
        # Verificar si ya existe
        mp3_path = os.path.join(self.output_dir, f"{title}.mp3")
        if os.path.exists(mp3_path):
            self.logger.info(f"Archivo ya existente: {mp3_path}")
            print(f"[INFO] Archivo ya existente: {mp3_path}")
            return mp3_path
        
        errors = []
        
        # 1. Intentar con pytube (más ligero y rápido)
        try:
            from pytube import YouTube
            
            def on_progress(stream, chunk, bytes_remaining):
                total_size = stream.filesize
                bytes_downloaded = total_size - bytes_remaining
                percentage = (bytes_downloaded / total_size) * 100
                print(f"\rProgreso: {percentage:.1f}%", end="")
            
            self.logger.info("Intentando descarga con pytube...")
            yt = YouTube(url, on_progress_callback=on_progress)
            
            streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
            if not streams:
                streams = yt.streams.filter(progressive=True).order_by('resolution').desc()
            
            if streams:
                stream = streams.first()
                print(f"[INFO] Descargando stream: {stream}")
                file_path = stream.download(output_path=self.output_dir, filename=title)
                print("\n[INFO] Descarga completada con pytube")
                
                if not file_path.endswith('.mp3'):
                    from pydub import AudioSegment
                    audio = AudioSegment.from_file(file_path)
                    mp3_path = os.path.join(self.output_dir, f"{title}.mp3")
                    audio.export(mp3_path, format='mp3')
                    os.remove(file_path)
                    file_path = mp3_path
                    print("[INFO] Archivo convertido a MP3")
                
                self.logger.info(f"Archivo guardado como: {file_path}")
                return file_path
                
        except Exception as e:
            error = f"Error con pytube: {str(e)}"
            self.logger.error(error)
            print(f"[ERROR] {error}")
            errors.append(error)
        
        # 2. Intentar con yt-dlp
        try:
            self.logger.info("Intentando descarga con yt-dlp...")
            print("[INFO] Intentando descarga con yt-dlp...")
            
            ydl_opts = self._get_ydl_opts()
            ydl_opts['outtmpl'] = os.path.join(self.output_dir, f"{title}.%(ext)s")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                mp3_path = os.path.join(self.output_dir, f"{title}.mp3")
                if os.path.exists(mp3_path):
                    self.logger.info(f"Archivo descargado con yt-dlp: {mp3_path}")
                    print(f"[INFO] Archivo descargado con yt-dlp: {mp3_path}")
                    return mp3_path
                    
        except Exception as e:
            error = f"Error con yt-dlp: {str(e)}"
            self.logger.error(error)
            print(f"[ERROR] {error}")
            errors.append(error)
            
        # 3. Intentar con youtube-dl como último recurso
        try:
            self.logger.info("Intentando descarga con youtube-dl...")
            print("[INFO] Intentando descarga con youtube-dl...")
            
            import youtube_dl
            
            ydl_opts = self._get_ydl_opts()
            ydl_opts['outtmpl'] = os.path.join(self.output_dir, f"{title}.%(ext)s")
            
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                mp3_path = os.path.join(self.output_dir, f"{title}.mp3")
                if os.path.exists(mp3_path):
                    self.logger.info(f"Archivo descargado con youtube-dl: {mp3_path}")
                    print(f"[INFO] Archivo descargado con youtube-dl: {mp3_path}")
                    return mp3_path
                    
        except Exception as e:
            error = f"Error con youtube-dl: {str(e)}"
            self.logger.error(error)
            print(f"[ERROR] {error}")
            errors.append(error)
            
        # Si llegamos aquí, ningún método funcionó
        error_msg = "No se pudo descargar con ningún método:\n" + "\n".join(errors)
        self.logger.error(error_msg)
        print(f"[ERROR] {error_msg}")
        return None

    def transcribe_video(self, file_path):
        """Transcribir un video usando el método configurado"""
        try:
            self.logger.info(f"Iniciando transcripción del archivo: {self._sanitize_text(file_path)}")
            print(f"[INFO] Iniciando transcripción del archivo: {self._sanitize_text(file_path)}")
            
            # Obtener duración del audio
            import subprocess
            try:
                cmd = ['ffmpeg', '-i', file_path]
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
                duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})", result.stderr)
                if duration_match:
                    hours, minutes, seconds = map(int, duration_match.groups())
                    duration = hours * 3600 + minutes * 60 + seconds
                    self.logger.info(f"Duración del audio: {duration} segundos")
                    print(f"[INFO] Duración del audio: {duration} segundos")
                else:
                    print("[WARNING] No se pudo obtener la duración del audio")
            except Exception as e:
                print(f"[WARNING] Error obteniendo duración: {str(e)}")
            
            # Si el archivo es muy grande, dividirlo
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # Tamaño en MB
            if file_size > 25:  # Si es mayor a 25MB
                self.logger.info(f"Archivo demasiado grande ({file_size:.2f}MB), dividiendo en segmentos...")
                print(f"[INFO] Archivo demasiado grande ({file_size:.2f}MB), dividiendo en segmentos...")
                return self._transcribe_large_file(file_path)
            
            # Intentar transcripción con el método configurado
            try:
                transcription = self.transcriber.transcribe(file_path)
                if not transcription:
                    raise Exception("La transcripción está vacía")
                    
                # Guardar transcripción
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                transcription_file = os.path.join(self.transcriptions_dir, f"{base_name}.txt")
                
                with open(transcription_file, 'w', encoding='utf-8') as f:
                    f.write(transcription)
                    
                self.logger.info(f"Transcripción guardada en: {self._sanitize_text(transcription_file)}")
                print(f"[INFO] Transcripción guardada en: {self._sanitize_text(transcription_file)}")
                return transcription_file
                
            except Exception as e:
                self.logger.error(f"Error con el método de transcripción principal: {str(e)}")
                print(f"[ERROR] Error con el método de transcripción principal: {str(e)}")
                
                # Intentar método alternativo
                if config.TRANSCRIPTION_METHOD == "api":
                    self.logger.info("Intentando transcripción local...")
                    print("[INFO] Intentando transcripción local...")
                    config.TRANSCRIPTION_METHOD = "local"
                    transcription = self.transcriber.transcribe(file_path)
                    if not transcription:
                        raise Exception("La transcripción está vacía")
                        
                    # Guardar transcripción
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    transcription_file = os.path.join(self.transcriptions_dir, f"{base_name}.txt")
                    
                    with open(transcription_file, 'w', encoding='utf-8') as f:
                        f.write(transcription)
                        
                    self.logger.info(f"Transcripción guardada en: {self._sanitize_text(transcription_file)}")
                    print(f"[INFO] Transcripción guardada en: {self._sanitize_text(transcription_file)}")
                    return transcription_file
                    
                raise Exception(f"No se pudo transcribir con ningún método: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"Error en transcripción: {str(e)}")
            print(f"[ERROR] Error en transcripción: {str(e)}")
            return None

    def _transcribe_large_file(self, file_path):
        """Handle transcription of files larger than 25MB by splitting them"""
        try:
            import ffmpeg
            
            # Get file info
            probe = ffmpeg.probe(file_path)
            duration = float(probe['streams'][0]['duration'])
            
            # Calculate number of segments needed (5 minutes each)
            SEGMENT_DURATION = 300  # 5 minutes in seconds
            num_segments = int(duration / SEGMENT_DURATION) + 1
            self.logger.info(f"Dividiendo archivo en {num_segments} segmentos de {SEGMENT_DURATION/60} minutos...")
            
            # Create temporary directory for segments
            with tempfile.TemporaryDirectory() as temp_dir:
                segments = []
                
                # Split file into segments
                for i in range(num_segments):
                    start_time = i * SEGMENT_DURATION
                    output_segment = os.path.join(temp_dir, f"segment_{i}.mp3")
                    
                    # Use ffmpeg to extract segment
                    stream = ffmpeg.input(file_path, ss=start_time, t=SEGMENT_DURATION)
                    stream = ffmpeg.output(stream, output_segment, acodec='libmp3lame', loglevel='error')
                    ffmpeg.run(stream, overwrite_output=True)
                    
                    segments.append(output_segment)
                    self.logger.info(f"Segmento {i+1}/{num_segments} creado")
                
                # Transcribe each segment in parallel
                from concurrent.futures import ThreadPoolExecutor
                transcriptions = []
                
                def transcribe_segment(segment):
                    self.logger.info(f"Transcribiendo segmento {segments.index(segment)+1}/{num_segments}...")
                    return self.transcriber.transcribe(segment)
                
                with ThreadPoolExecutor(max_workers=3) as executor:
                    transcriptions = list(executor.map(transcribe_segment, segments))
                
                # Combine transcriptions
                full_transcription = "\n".join(filter(None, transcriptions))
                
                # Save full transcription
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                transcription_file = os.path.join(self.transcriptions_dir, f"{base_name}.txt")
                
                with open(transcription_file, 'w', encoding='utf-8') as f:
                    f.write(full_transcription)
                
                self.logger.info(f"Transcripción completa guardada en: {self._sanitize_text(transcription_file)}")
                return transcription_file
                
        except Exception as e:
            self.logger.error(f"Error durante la transcripción de archivo grande: {str(e)}")
            raise

    def summarize_transcription(self, transcription_file):
        """Generar resumen de la transcripción usando el método configurado"""
        try:
            self.logger.info(f"Iniciando resumen de: {transcription_file}")
            print(f"[INFO] Iniciando resumen de: {transcription_file}")
            
            # Leer transcripción
            with open(transcription_file, 'r', encoding='utf-8') as f:
                transcription = f.read()
                
            if not transcription:
                raise Exception("La transcripción está vacía")
            
            # Intentar resumen con el método configurado
            try:
                summary = self.summarizer.summarize(transcription)
                if not summary:
                    raise Exception("El resumen está vacío")
                    
                # Guardar resumen original
                base_name = os.path.splitext(os.path.basename(transcription_file))[0].replace('_transcription', '')
                summary_file = os.path.join(self.summaries_dir, f"{base_name}_summary.txt")
                
                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write(summary)
                    
                self.logger.info(f"Resumen guardado en: {summary_file}")
                print(f"[INFO] Resumen guardado en: {summary_file}")
                
                # Traducir el resumen (no la transcripción completa)
                try:
                    # Traducir a español
                    summary_es = self.summarizer.translate(summary, target_lang='es')
                    summary_file_es = os.path.join(self.summaries_dir, f"{base_name}_summary_es.txt")
                    with open(summary_file_es, 'w', encoding='utf-8') as f:
                        f.write(summary_es)
                    self.logger.info(f"Resumen en español guardado en: {summary_file_es}")
                    print(f"[INFO] Resumen en español guardado en: {summary_file_es}")
                    
                    # Traducir a inglés
                    summary_en = self.summarizer.translate(summary, target_lang='en')
                    summary_file_en = os.path.join(self.summaries_dir, f"{base_name}_summary_en.txt")
                    with open(summary_file_en, 'w', encoding='utf-8') as f:
                        f.write(summary_en)
                    self.logger.info(f"Resumen en inglés guardado en: {summary_file_en}")
                    print(f"[INFO] Resumen en inglés guardado en: {summary_file_en}")
                    
                    return [summary_file, summary_file_es, summary_file_en]
                    
                except Exception as e:
                    self.logger.error(f"Error en traducción: {str(e)}")
                    print(f"[ERROR] Error en traducción: {str(e)}")
                    # Si falla la traducción, devolver al menos el resumen original
                    return [summary_file]
                
            except Exception as e:
                self.logger.error(f"Error con el método de resumen principal: {str(e)}")
                print(f"[ERROR] Error con el método de resumen principal: {str(e)}")
                
                # Intentar método alternativo
                if config.SUMMARIZATION_METHOD == "openai":
                    self.logger.info("Intentando resumen con modelo local...")
                    print("[INFO] Intentando resumen con modelo local...")
                    config.SUMMARIZATION_METHOD = "llama"
                    summary = self.summarizer.summarize(transcription)
                    if not summary:
                        raise Exception("El resumen está vacío")
                        
                    # Guardar resumen
                    base_name = os.path.splitext(os.path.basename(transcription_file))[0].replace('_transcription', '')
                    summary_file = os.path.join(self.summaries_dir, f"{base_name}_summary.txt")
                    
                    with open(summary_file, 'w', encoding='utf-8') as f:
                        f.write(summary)
                        
                    self.logger.info(f"Resumen guardado en: {summary_file}")
                    print(f"[INFO] Resumen guardado en: {summary_file}")
                    return [summary_file]
                    
                raise Exception(f"No se pudo generar el resumen con ningún método: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"Error en resumen: {str(e)}")
            print(f"[ERROR] Error en resumen: {str(e)}")
            return None

    def process_url(self, url, i, total_urls):
        """Procesar una URL individual con reintentos"""
        max_retries = 3
        retry_delay = 5  # segundos
        
        for attempt in range(max_retries):
            try:
                self._log_info(f"Procesando URL {i}/{total_urls} (Intento {attempt + 1}/{max_retries})", {'url': url})
                
                # Verificar checkpoint
                checkpoint_status = self._get_checkpoint_status(url)
                success = True
                error_details = []
                
                # 1. Descarga
                file_path = None
                if 'download' not in checkpoint_status:
                    self._log_info("ETAPA 1: Descarga de video")
                    
                    try:
                        file_path = self.download_video(url)
                        if file_path:
                            self._save_checkpoint(url, 'download', 'completed')
                            self._log_info("Descarga completada", {'file_path': file_path})
                        else:
                            error_details.append("Fallo en descarga")
                            success = False
                            self._log_error("Error en descarga", Exception("No se pudo descargar el video"), {'url': url})
                    except Exception as e:
                        error_details.append(f"Error en descarga: {str(e)}")
                        success = False
                        self._log_error("Error en descarga", e, {'url': url})
                else:
                    self._log_info("Descarga ya completada, buscando archivo...")
                    try:
                        file_path = self._find_audio_file(url)
                        if file_path:
                            self._log_info("Archivo encontrado", {'file_path': file_path})
                        else:
                            error_details.append("No se encontró el archivo")
                            success = False
                            self._log_warning("Archivo no encontrado", {'url': url})
                    except Exception as e:
                        error_details.append(f"Error buscando archivo: {str(e)}")
                        success = False
                        self._log_error("Error buscando archivo", e, {'url': url})
                
                # 2. Transcripción
                transcription_file = None
                if success and file_path and 'transcription' not in checkpoint_status:
                    self._log_info("ETAPA 2: Transcripción")
                    
                    try:
                        transcription_file = self.transcribe_video(file_path)
                        if transcription_file:
                            self._save_checkpoint(url, 'transcription', 'completed')
                            self._log_info("Transcripción completada", {'file_path': transcription_file})
                        else:
                            error_details.append("Fallo en transcripción")
                            success = False
                            self._log_error("Error en transcripción", Exception("No se pudo transcribir el video"), {'file_path': file_path})
                    except Exception as e:
                        error_details.append(f"Error en transcripción: {str(e)}")
                        success = False
                        self._log_error("Error en transcripción", e, {'file_path': file_path})
                elif success and file_path:
                    self._log_info("Transcripción ya completada, buscando archivo...")
                    try:
                        transcription_file = self._find_transcription_file(url)
                        if transcription_file:
                            self._log_info("Archivo de transcripción encontrado", {'file_path': transcription_file})
                        else:
                            error_details.append("No se encontró el archivo de transcripción")
                            success = False
                            self._log_warning("Archivo de transcripción no encontrado", {'url': url})
                    except Exception as e:
                        error_details.append(f"Error buscando transcripción: {str(e)}")
                        success = False
                        self._log_error("Error buscando transcripción", e, {'url': url})
                
                # 3. Resumen
                if success and transcription_file and 'summary' not in checkpoint_status:
                    self._log_info("ETAPA 3: Generación de resumen")
                    
                    try:
                        summary_files = self.summarize_transcription(transcription_file)
                        if summary_files:
                            self._save_checkpoint(url, 'summary', 'completed')
                            self._log_info("Resumen completado", {'files': summary_files})
                        else:
                            error_details.append("Fallo en resumen")
                            success = False
                            self._log_error("Error en resumen", Exception("No se pudo generar el resumen"), {'transcription_file': transcription_file})
                    except Exception as e:
                        error_details.append(f"Error en resumen: {str(e)}")
                        success = False
                        self._log_error("Error en resumen", e, {'transcription_file': transcription_file})
                elif success and transcription_file:
                    self._log_info("Resumen ya completado, buscando archivos...")
                    try:
                        summary_files = self._find_summary_files(url)
                        if summary_files:
                            self._log_info("Archivos de resumen encontrados", {'files': summary_files})
                        else:
                            error_details.append("No se encontraron los archivos de resumen")
                            success = False
                            self._log_warning("Archivos de resumen no encontrados", {'url': url})
                    except Exception as e:
                        error_details.append(f"Error buscando resúmenes: {str(e)}")
                        success = False
                        self._log_error("Error buscando resúmenes", e, {'url': url})
                
                # Registrar uso si hubo éxito
                if success:
                    try:
                        self._log_usage(url)
                        self._log_info("Uso registrado correctamente")
                    except Exception as e:
                        self._log_error("Error registrando uso", e, {'url': url})
                
                # Registrar resultado final
                if success:
                    self._log_info("Proceso completado", {'url': url})
                    return True
                else:
                    error_msg = f"Errores procesando {url}: {'; '.join(error_details)}"
                    self._log_error("Proceso fallido", Exception(error_msg), {'url': url, 'details': error_details})
                    self._save_checkpoint(url, 'error', '; '.join(error_details))
                    
                    if attempt < max_retries - 1:
                        self._log_info(f"Reintentando en {retry_delay} segundos...")
                        import time
                        time.sleep(retry_delay)
                        continue
                    return False
                
            except Exception as e:
                self._log_error("Error crítico procesando URL", e, {'url': url, 'position': f"{i}/{total_urls}"})
                self._save_checkpoint(url, 'error', str(e))
                
                if attempt < max_retries - 1:
                    self._log_info(f"Reintentando en {retry_delay} segundos...")
                    import time
                    time.sleep(retry_delay)
                    continue
                return False
        
        return False

    def download_from_file(self, urls_file):
        """Descargar videos desde un archivo de URLs"""
        try:
            # Actualizar dependencias al inicio
            self._update_dependencies()
            
            # Leer URLs del archivo
            if not os.path.exists(urls_file):
                self._log_error("Archivo de URLs no encontrado", FileNotFoundError(urls_file))
                return []
                
            with open(urls_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f.readlines() if line.strip()]
                
            if not urls:
                self._log_warning("No se encontraron URLs en el archivo")
                return []
                
            self._log_info(f"Procesando {len(urls)} URLs...")
            
            # Procesar cada URL de forma independiente
            results = []
            failed_urls = []
            
            # Crear un pool de workers para procesar URLs en paralelo
            from concurrent.futures import ThreadPoolExecutor, as_completed
            max_workers = min(3, len(urls))  # Máximo 3 URLs simultáneas
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Enviar todas las URLs al pool
                future_to_url = {
                    executor.submit(self.process_url, url, i, len(urls)): url 
                    for i, url in enumerate(urls, 1)
                }
                
                # Procesar resultados conforme se completan
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        success = future.result()
                        if success:
                            results.append(url)
                            self._log_info(f"URL procesada exitosamente", {'url': url})
                        else:
                            failed_urls.append(url)
                            self._log_warning(f"URL fallida", {'url': url})
                    except Exception as e:
                        failed_urls.append(url)
                        self._log_error(f"Error procesando URL", e, {'url': url})
            
            # Resumen final
            total = len(urls)
            successful = len(results)
            failed = len(failed_urls)
            
            summary = {
                'total_urls': total,
                'successful': successful,
                'failed': failed,
                'successful_urls': results,
                'failed_urls': failed_urls
            }
            
            self._log_info("RESUMEN FINAL", summary)
            
            if failed > 0:
                self._log_warning("Algunas URLs fallaron", {
                    'failed_count': failed,
                    'failed_urls': failed_urls
                })
            
            return results
            
        except Exception as e:
            self._log_error("Error crítico procesando archivo de URLs", e)
            return []

    def _find_audio_file(self, url):
        """Buscar archivo de audio existente para una URL"""
        try:
            from pytube import YouTube
            yt = YouTube(url)
            title = self._sanitize_filename(yt.title)
            
            # Buscar archivo MP3
            mp3_path = os.path.join(self.output_dir, f"{title}.mp3")
            if os.path.exists(mp3_path):
                return mp3_path
                
            # Buscar otros formatos de audio
            for ext in ['.m4a', '.webm', '.wav']:
                file_path = os.path.join(self.output_dir, f"{title}{ext}")
                if os.path.exists(file_path):
                    return file_path
                    
        except Exception as e:
            self.logger.debug(f"Error buscando archivo de audio: {str(e)}")
            
        return None
        
    def _find_transcription_file(self, url):
        """Buscar archivo de transcripción existente para una URL"""
        try:
            from pytube import YouTube
            yt = YouTube(url)
            title = self._sanitize_filename(yt.title)
            
            # Buscar archivo de transcripción
            transcription_path = os.path.join(self.transcriptions_dir, f"{title}.txt")
            if os.path.exists(transcription_path):
                return transcription_path
                
        except Exception as e:
            self.logger.debug(f"Error buscando archivo de transcripción: {str(e)}")
            
        return None
        
    def _find_summary_files(self, url):
        """Buscar archivos de resumen existentes para una URL"""
        try:
            from pytube import YouTube
            yt = YouTube(url)
            title = self._sanitize_filename(yt.title)
            
            # Buscar archivos de resumen
            summary_path = os.path.join(self.summaries_dir, f"{title}_summary.txt")
            if os.path.exists(summary_path):
                return [summary_path]
                
        except Exception as e:
            self.logger.debug(f"Error buscando archivos de resumen: {str(e)}")
            
        return None

    def _get_video_title(self, url):
        """Obtener título del video para usar como nombre de archivo"""
        try:
            # Intentar con yt-dlp primero (más robusto)
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'no_playlist': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', None)
                
                if title:
                    # Limpiar caracteres no válidos para nombre de archivo
                    title = self._sanitize_text(title)
                    return title
                    
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error obteniendo título del video con yt-dlp: {str(e)}")
            print(f"[ERROR] Error obteniendo título del video con yt-dlp: {str(e)}")
            
            # Intentar con pytube como respaldo
            try:
                from pytube import YouTube
                yt = YouTube(url)
                title = yt.title
                if title:
                    title = self._sanitize_text(title)
                    return title
            except Exception as e2:
                if hasattr(self, 'logger'):
                    self.logger.error(f"Error obteniendo título del video con pytube: {str(e2)}")
                print(f"[ERROR] Error obteniendo título del video con pytube: {str(e2)}")
        
        # Si todo falla, usar un nombre genérico con timestamp
        if hasattr(self, 'logger'):
            self.logger.error(f"Error obteniendo título del video: {str(e)}")
        print(f"[ERROR] Error obteniendo título del video. Usando nombre genérico.")
        return f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _sanitize_filename(self, filename):
        """Eliminar caracteres problemáticos del nombre del archivo"""
        return self._sanitize_text(filename)
            
    def _get_ydl_opts(self):
        """Obtener opciones para yt-dlp"""
        return {
            'format': 'm4a/bestaudio/best',  # Try m4a first
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': True,
            'no_color': True,
            'extractor_retries': 3,
            'file_access_retries': 3,
            'fragment_retries': 3,
            'skip_unavailable_fragments': True,
            'overwrites': True,
            'extract_flat': False,
            'concurrent_fragments': 5
        }
        
    def _remove_emojis(self, text):
        return re.sub(r'[\U00010000-\U0010ffff]', '', text)
        
    def _delete_duplicates(self):
        """Eliminar archivos duplicados en el directorio de salida"""
        try:
            self.logger.info("Buscando archivos duplicados...")
            
            if not os.path.exists(self.output_dir):
                self.logger.warning(f"El directorio {self.output_dir} no existe")
                return
            
            # Obtener lista de archivos
            files = os.listdir(self.output_dir)
            
            # Agrupar por nombre base (sin extensión)
            file_groups = {}
            for file in files:
                base_name = os.path.splitext(file)[0]
                if base_name not in file_groups:
                    file_groups[base_name] = []
                file_groups[base_name].append(file)
                
            # Buscar grupos con más de un archivo
            duplicates_found = False
            for base_name, group in file_groups.items():
                if len(group) > 1:
                    duplicates_found = True
                    self.logger.info(f"Encontrados archivos duplicados para '{base_name}': {group}")
                    
                    # Mantener solo el archivo MP3 si existe, o el más grande
                    mp3_files = [f for f in group if f.endswith('.mp3')]
                    if mp3_files:
                        # Mantener el MP3, eliminar el resto
                        for file in group:
                            if file not in mp3_files:
                                try:
                                    os.remove(os.path.join(self.output_dir, file))
                                    self.logger.info(f"Eliminado archivo duplicado: {file}")
                                except Exception as e:
                                    self.logger.error(f"Error eliminando archivo {file}: {str(e)}")
                    else:
                        # No hay MP3, mantener el archivo más grande
                        file_sizes = [(f, os.path.getsize(os.path.join(self.output_dir, f))) for f in group]
                        file_sizes.sort(key=lambda x: x[1], reverse=True)
                        largest_file = file_sizes[0][0]
                        
                        for file, _ in file_sizes[1:]:
                            try:
                                os.remove(os.path.join(self.output_dir, file))
                                self.logger.info(f"Eliminado archivo duplicado: {file}")
                            except Exception as e:
                                self.logger.error(f"Error eliminando archivo {file}: {str(e)}")
                                
            if not duplicates_found:
                self.logger.info("No se encontraron archivos duplicados")
                
        except Exception as e:
            self.logger.error(f"Error buscando duplicados: {str(e)}")

    def generate_recommendations_from_logs(self, log_file=None):
        """
        Genera recomendaciones de depuración y refactorización a partir de un archivo de log específico
        o del archivo de log más reciente si no se especifica.
        
        Args:
            log_file (str, optional): Ruta al archivo de log específico. Si es None, se usa el más reciente.
        
        Returns:
            str: Ruta al archivo de recomendaciones generado, o None si hubo un error
        """
        try:
            self._log_info("Generando recomendaciones de depuración y refactorización...")
            print("[INFO] Generando recomendaciones de depuración y refactorización...")
            
            # Si no se especificó un archivo de log, buscar el más reciente
            if log_file is None:
                log_dir = self.log_dir
                if not os.path.exists(log_dir):
                    self._log_warning(f"El directorio de logs {log_dir} no existe")
                    print(f"[ADVERTENCIA] El directorio de logs {log_dir} no existe")
                    return None
                    
                log_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith('.log')]
                if not log_files:
                    self._log_warning("No se encontraron archivos de log")
                    print("[ADVERTENCIA] No se encontraron archivos de log")
                    return None
                    
                log_file = max(log_files, key=os.path.getmtime)
                
            if not os.path.exists(log_file):
                self._log_warning(f"El archivo de log {log_file} no existe")
                print(f"[ADVERTENCIA] El archivo de log {log_file} no existe")
                return None
                
            self._log_info(f"Usando archivo de log: {log_file}")
            print(f"[INFO] Usando archivo de log: {log_file}")
            
            # Crear el generador de recomendaciones
            recommendation_generator = RecommendationGenerator()
            
            if not recommendation_generator.available:
                self._log_warning("No se puede generar recomendaciones: API de OpenAI no disponible")
                print("[ADVERTENCIA] No se puede generar recomendaciones: API de OpenAI no disponible")
                return None
            
            # Generar nombre para el archivo de recomendaciones
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            recommendations_dir = os.path.join(self.base_dir, 'recommendations')
            os.makedirs(recommendations_dir, exist_ok=True)
            recommendations_file = os.path.join(recommendations_dir, f"recommendations_{timestamp}.md")
            
            # Generar recomendaciones
            success = recommendation_generator.generate_from_log_file(log_file, recommendations_file)
            
            if success:
                self._log_info(f"Recomendaciones generadas correctamente: {recommendations_file}")
                print(f"[INFO] Recomendaciones generadas correctamente: {recommendations_file}")
                return recommendations_file
            else:
                self._log_warning("No se pudieron generar las recomendaciones")
                print("[ADVERTENCIA] No se pudieron generar las recomendaciones")
                return None
                
        except Exception as e:
            self._log_error("Error generando recomendaciones", e)
            print(f"[ERROR] Error generando recomendaciones: {str(e)}")
            return None


def main():
    """
    Función principal para ejecutar el downloader desde línea de comandos
    con soporte para diferentes comandos y opciones
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube Downloader con transcripción y resumen')
    subparsers = parser.add_subparsers(dest='command', help='Comando a ejecutar')
    
    # Comando para descargar videos
    download_parser = subparsers.add_parser('download', help='Descargar videos desde un archivo de URLs')
    download_parser.add_argument('urls_file', help='Archivo con URLs de YouTube (una por línea)')
    
    # Comando para generar recomendaciones
    recommend_parser = subparsers.add_parser('recommend', help='Generar recomendaciones de depuración y refactorización')
    recommend_parser.add_argument('--log-file', help='Archivo de log específico (opcional, por defecto usa el más reciente)')
    
    # Comando para limpiar duplicados
    clean_parser = subparsers.add_parser('clean', help='Eliminar archivos duplicados')
    
    # Parsear argumentos
    args = parser.parse_args()
    
    # Crear instancia del downloader
    downloader = YouTubeDownloader()
    
    # Ejecutar el comando correspondiente
    if args.command == 'download':
        print(f"[INFO] Descargando videos desde {args.urls_file}...")
        downloader.download_from_file(args.urls_file)
        # Generar recomendaciones automáticamente al finalizar la descarga
        downloader.generate_recommendations_from_logs()
        
    elif args.command == 'recommend':
        print("[INFO] Generando recomendaciones...")
        recommendations_file = downloader.generate_recommendations_from_logs(args.log_file)
        if recommendations_file:
            print(f"[INFO] Recomendaciones guardadas en: {recommendations_file}")
        else:
            print("[ERROR] No se pudieron generar las recomendaciones")
            
    elif args.command == 'clean':
        print("[INFO] Eliminando archivos duplicados...")
        downloader._delete_duplicates()
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()                    self.logger.info(f"Archivo duplicado eliminado: {filename}")
                else:
                    seen.add(filename)

    def generate_recommendations_from_logs(self, log_file=None):
        """
        Genera recomendaciones de depuración y refactorización a partir de un archivo de log específico
        o del archivo de log más reciente si no se especifica.
        
        Args:
            log_file (str, optional): Ruta al archivo de log específico. Si es None, se usa el más reciente.
            
        Returns:
            str: Ruta al archivo de recomendaciones generado, o None si hubo un error
        """
        try:
            self._log_info("Generando recomendaciones de depuración y refactorización...")
            print("[INFO] Generando recomendaciones de depuración y refactorización...")
            
            # Si no se especificó un archivo de log, buscar el más reciente
            if log_file is None:
                log_dir = self.log_dir
                if not os.path.exists(log_dir):
                    self._log_warning(f"El directorio de logs {log_dir} no existe")
                    print(f"[ADVERTENCIA] El directorio de logs {log_dir} no existe")
                    return None
                    
                log_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith('.log')]
                if not log_files:
                    self._log_warning("No se encontraron archivos de log")
                    print("[ADVERTENCIA] No se encontraron archivos de log")
                    return None
                    
                log_file = max(log_files, key=os.path.getmtime)
                
            if not os.path.exists(log_file):
                self._log_warning(f"El archivo de log {log_file} no existe")
                print(f"[ADVERTENCIA] El archivo de log {log_file} no existe")
                return None
                
            self._log_info(f"Usando archivo de log: {log_file}")
            print(f"[INFO] Usando archivo de log: {log_file}")
            
            # Crear el generador de recomendaciones
            try:
                from .models import RecommendationGenerator
            except ImportError:
                # Si estamos ejecutando directamente este archivo, importar de otra manera
                import sys
                import os.path
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from src.models import RecommendationGenerator
                
            recommendation_generator = RecommendationGenerator()
            
            if not recommendation_generator.available:
                self._log_warning("No se puede generar recomendaciones: API de OpenAI no disponible")
                print("[ADVERTENCIA] No se puede generar recomendaciones: API de OpenAI no disponible")
                return None
            
            # Generar nombre para el archivo de recomendaciones
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            recommendations_dir = os.path.join(self.base_dir, 'recommendations')
            os.makedirs(recommendations_dir, exist_ok=True)
            recommendations_file = os.path.join(recommendations_dir, f"recommendations_{timestamp}.md")
            
            # Generar recomendaciones
            success = recommendation_generator.generate_from_log_file(log_file, recommendations_file)
            
            if success:
                self._log_info(f"Recomendaciones generadas correctamente: {recommendations_file}")
                print(f"[INFO] Recomendaciones generadas correctamente: {recommendations_file}")
                return recommendations_file
            else:
                self._log_warning("No se pudieron generar las recomendaciones")
                print("[ADVERTENCIA] No se pudieron generar las recomendaciones")
                return None
                
        except Exception as e:
            self._log_error("Error generando recomendaciones", e)
            print(f"[ERROR] Error generando recomendaciones: {str(e)}")
            return None


def main():
    """
    Función principal para ejecutar el downloader desde línea de comandos
    con soporte para diferentes comandos y opciones
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube Downloader con transcripción y resumen')
    subparsers = parser.add_subparsers(dest='command', help='Comando a ejecutar')
    
    # Comando para descargar videos
    download_parser = subparsers.add_parser('download', help='Descargar videos desde un archivo de URLs')
    download_parser.add_argument('urls_file', help='Archivo con URLs de YouTube (una por línea)')
    
    # Comando para generar recomendaciones
    recommend_parser = subparsers.add_parser('recommend', help='Generar recomendaciones de depuración y refactorización')
    recommend_parser.add_argument('--log-file', help='Archivo de log específico (opcional, por defecto usa el más reciente)')
    
    # Comando para limpiar duplicados
    clean_parser = subparsers.add_parser('clean', help='Eliminar archivos duplicados')
    
    # Parsear argumentos
    args = parser.parse_args()
    
    # Crear instancia del downloader
    downloader = YouTubeDownloader()
    
    # Ejecutar el comando correspondiente
    if args.command == 'download':
        print(f"[INFO] Descargando videos desde {args.urls_file}...")
        downloader.download_from_file(args.urls_file)
        # La generación de recomendaciones ya se hace automáticamente al finalizar la descarga
        
    elif args.command == 'recommend':
        print("[INFO] Generando recomendaciones...")
        recommendations_file = downloader.generate_recommendations_from_logs(args.log_file)
        if recommendations_file:
            print(f"[INFO] Recomendaciones guardadas en: {recommendations_file}")
        else:
            print("[ERROR] No se pudieron generar las recomendaciones")
            
    elif args.command == 'clean':
        print("[INFO] Eliminando archivos duplicados...")
        downloader._delete_duplicates()
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()