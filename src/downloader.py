import os
import yt_dlp
import logging
import re
from datetime import datetime
from . import config
from .models import Transcriber, Summarizer, OpenAISummarizer
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
        
        # Actualizar dependencias al inicio
        self._update_dependencies()
        
        self.transcriber = Transcriber.get_transcriber()
        self.summarizer = Summarizer.get_summarizer()
        self._setup_logging()
        self._ensure_directories()
        self.usage_data = {
            'whisper': {'seconds': 0, 'cost_per_minute': 0.006},  # $0.006 per minute
            'gpt-3.5-turbo': {'input_tokens': 0, 'output_tokens': 0, 'cost_per_1k_input': 0.0015, 'cost_per_1k_output': 0.002},  # $0.0015/1K input, $0.002/1K output
            'gpt-4': {'input_tokens': 0, 'output_tokens': 0, 'cost_per_1k_input': 0.03, 'cost_per_1k_output': 0.06}  # $0.03/1K input, $0.06/1K output
        }
        
    def _setup_logging(self):
        """Configurar logging específico para el downloader"""
        self.logger = logging.getLogger('downloader')
        self.logger.setLevel(logging.INFO)
        
        # Limpiar handlers existentes
        self.logger.handlers = []
        
        # Handler para archivo con encoding UTF-8
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.log_dir, f'process_{timestamp}.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_format = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
        
        # Handler para consola con encoding UTF-8
        console_handler = logging.StreamHandler(sys.stdout)
        console_format = logging.Formatter('[%(levelname)s] %(message)s')
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)

        # Remove emojis and special characters from logs
        for handler in self.logger.handlers:
            handler.addFilter(lambda record: setattr(record, 'msg', self._sanitize_text(str(record.msg))) or True)
            
    def _sanitize_text(self, text):
        """Eliminar caracteres problemáticos del texto"""
        # Eliminar emojis y caracteres especiales
        text = re.sub(r'[^\x00-\x7F]+', '', text)
        # Reemplazar caracteres no permitidos con guion bajo
        text = re.sub(r'[<>:"/\\|?*\u200d]', '_', text)
        # Eliminar espacios múltiples
        text = re.sub(r'\s+', ' ', text).strip()
        return text
            
    def _ensure_directories(self):
        """Asegurar que existen todos los directorios necesarios"""
        for dir_path in [self.output_dir, self.transcriptions_dir, self.summaries_dir, self.log_dir, self.usage_log_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                self.logger.info(f"Directorio creado: {dir_path}")

    def _save_checkpoint(self, url, stage, status):
        """Guardar checkpoint del proceso"""
        try:
            with open(self.checkpoint_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{timestamp}|{url}|{stage}|{status}\n")
        except Exception as e:
            self.logger.error(f"Error al guardar checkpoint: {str(e)}")

    def _get_checkpoint_status(self, url):
        """Obtener estado del último checkpoint para una URL"""
        if not os.path.exists(self.checkpoint_file):
            return {}
        
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                status = {}
                for line in reversed(lines):
                    timestamp, checkpoint_url, stage, checkpoint_status = line.strip().split('|')
                    if checkpoint_url == url and checkpoint_status == 'completed':
                        status[stage] = True
                return status
        except Exception as e:
            self.logger.error(f"Error al leer checkpoint: {str(e)}")
            return {}

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
        seen = set()
        for filename in os.listdir(self.output_dir):
            filepath = os.path.join(self.output_dir, filename)
            if os.path.isfile(filepath):
                if filename in seen:
                    os.remove(filepath)
                    self.logger.info(f"Archivo duplicado eliminado: {filename}")
                else:
                    seen.add(filename)

    def _update_dependencies(self):
        """Actualizar las dependencias de descarga"""
        try:
            import subprocess
            print("[INFO] Actualizando dependencias...")
            
            # Actualizar yt-dlp
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"], capture_output=True)
            print("[INFO] yt-dlp actualizado")
            
            # Actualizar pytube
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pytube"], capture_output=True)
            print("[INFO] pytube actualizado")
            
            # Actualizar youtube-dl
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "youtube-dl"], capture_output=True)
            print("[INFO] youtube-dl actualizado")
            
            # Actualizar ffmpeg-python
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "ffmpeg-python"], capture_output=True)
            print("[INFO] ffmpeg-python actualizado")
            
            # Actualizar pydub
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pydub"], capture_output=True)
            print("[INFO] pydub actualizado")
            
        except Exception as e:
            print(f"[ERROR] Error actualizando dependencias: {str(e)}")

    def download_video(self, url):
        """Descargar un video de YouTube usando múltiples métodos"""
        self.logger.info(f"Iniciando descarga para: {url}")
        print(f"[INFO] Iniciando descarga para: {url}")
        
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
            print(f"\n[INFO] Título del video: {yt.title}")
            
            streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
            if not streams:
                streams = yt.streams.filter(progressive=True).order_by('resolution').desc()
            
            if streams:
                stream = streams.first()
                print(f"[INFO] Descargando stream: {stream}")
                file_path = stream.download(output_path=self.output_dir)
                print("\n[INFO] Descarga completada con pytube")
                
                if not file_path.endswith('.mp3'):
                    from pydub import AudioSegment
                    audio = AudioSegment.from_file(file_path)
                    mp3_path = file_path.rsplit('.', 1)[0] + '.mp3'
                    audio.export(mp3_path, format='mp3')
                    os.remove(file_path)
                    file_path = mp3_path
                    print("[INFO] Archivo convertido a MP3")
                
                self.logger.info(f"Archivo guardado como: {file_path}")
                return file_path
                
        except Exception as e:
            self.logger.error(f"Error con pytube: {str(e)}")
            print(f"[ERROR] Error con pytube: {str(e)}")

        # 2. Intentar con yt-dlp (más robusto)
        try:
            self.logger.info("Intentando descarga con yt-dlp...")
            ydl_opts = self._get_ydl_opts()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print("[INFO] Descargando con yt-dlp...")
                result = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(result)
                file_path = file_path.replace('.webm', '.mp3').replace('.m4a', '.mp3')
                if os.path.exists(file_path):
                    print("[INFO] Descarga completada con yt-dlp")
                    self.logger.info(f"Archivo guardado como: {file_path}")
                    return file_path
                
        except Exception as e:
            self.logger.error(f"Error con yt-dlp: {str(e)}")
            print(f"[ERROR] Error con yt-dlp: {str(e)}")

        # 3. Intentar con youtube-dl (última opción)
        try:
            import youtube_dl
            self.logger.info("Intentando descarga con youtube-dl...")
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
            }
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                print("[INFO] Descargando con youtube-dl...")
                result = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(result)
                file_path = file_path.replace('.webm', '.mp3').replace('.m4a', '.mp3')
                if os.path.exists(file_path):
                    print("[INFO] Descarga completada con youtube-dl")
                    self.logger.info(f"Archivo guardado como: {file_path}")
                    return file_path
                
        except Exception as e:
            self.logger.error(f"Error con youtube-dl: {str(e)}")
            print(f"[ERROR] Error con youtube-dl: {str(e)}")

        self.logger.error("Todos los métodos de descarga fallaron")
        print("[ERROR] No se pudo descargar el video con ningún método")
        return None

    def _log_usage(self, url):
        """Log token usage and cost estimation"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            usage_file = os.path.join(self.usage_log_dir, f'usage_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
            
            total_cost_eur = 0
            
            with open(usage_file, 'w', encoding='utf-8') as f:
                f.write(f"=== REPORTE DE USO ===\n")
                f.write(f"Fecha y hora: {timestamp}\n")
                f.write(f"URL: {url}\n")
                f.write("=" * 50 + "\n\n")
                
                # Whisper usage
                minutes = self.usage_data['whisper']['seconds'] / 60
                whisper_cost = minutes * self.usage_data['whisper']['cost_per_minute']
                total_cost_eur += whisper_cost * 0.92  # Convert USD to EUR
                
                f.write("Whisper API:\n")
                f.write(f"- Duración del audio: {minutes:.2f} minutos\n")
                f.write(f"- Coste estimado: €{whisper_cost * 0.92:.4f}\n\n")
                
                # GPT usage
                model = config.OPENAI_MODEL
                if model in self.usage_data:
                    input_tokens = self.usage_data[model]['input_tokens']
                    output_tokens = self.usage_data[model]['output_tokens']
                    input_cost = (input_tokens / 1000) * self.usage_data[model]['cost_per_1k_input']
                    output_cost = (output_tokens / 1000) * self.usage_data[model]['cost_per_1k_output']
                    total_cost_eur += (input_cost + output_cost) * 0.92
                    
                    f.write(f"{model}:\n")
                    f.write(f"- Tokens de entrada: {input_tokens:,}\n")
                    f.write(f"- Tokens de salida: {output_tokens:,}\n")
                    f.write(f"- Coste estimado: €{(input_cost + output_cost) * 0.92:.4f}\n\n")
                
                f.write("-" * 50 + "\n")
                f.write(f"COSTE TOTAL: €{total_cost_eur:.4f}\n")
                f.write("-" * 50 + "\n")
                
        except Exception as e:
            self.logger.error(f"Error logging usage data: {str(e)}")

    def transcribe_video(self, file_path):
        """Transcribir un video usando el método configurado"""
        try:
            self.logger.info(f"Iniciando transcripción del archivo: {file_path}")
            print(f"[INFO] Iniciando transcripción del archivo: {file_path}")
            
            # Obtener duración del audio
            import subprocess
            cmd = ['ffmpeg', '-i', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})", result.stderr)
            if duration_match:
                hours, minutes, seconds = map(int, duration_match.groups())
                duration = hours * 3600 + minutes * 60 + seconds
                self.logger.info(f"Duración del audio: {duration} segundos")
                print(f"[INFO] Duración del audio: {duration} segundos")
            else:
                raise Exception("No se pudo obtener la duración del audio")
            
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
                transcription_file = os.path.join(self.transcriptions_dir, f"{base_name}_transcription.txt")
                
                with open(transcription_file, 'w', encoding='utf-8') as f:
                    f.write(transcription)
                    
                self.logger.info(f"Transcripción guardada en: {transcription_file}")
                print(f"[INFO] Transcripción guardada en: {transcription_file}")
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
                    transcription_file = os.path.join(self.transcriptions_dir, f"{base_name}_transcription.txt")
                    
                    with open(transcription_file, 'w', encoding='utf-8') as f:
                        f.write(transcription)
                        
                    self.logger.info(f"Transcripción guardada en: {transcription_file}")
                    print(f"[INFO] Transcripción guardada en: {transcription_file}")
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
            
            # Calculate number of segments needed (10 minutes each)
            SEGMENT_DURATION = 600  # 10 minutes in seconds
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
                
                # Transcribe each segment
                transcriptions = []
                for i, segment in enumerate(segments):
                    self.logger.info(f"Transcribiendo segmento {i+1}/{num_segments}...")
                    transcription = self.transcriber.transcribe(segment)
                    transcriptions.append(transcription)
                    self.logger.info(f"Segmento {i+1} transcrito exitosamente")
                
                # Combine transcriptions
                full_transcription = "\n".join(transcriptions)
                
                # Save full transcription
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                transcription_file = os.path.join(self.transcriptions_dir, f"{base_name}.txt")
                
                with open(transcription_file, 'w', encoding='utf-8') as f:
                    f.write(full_transcription)
                
                self.logger.info(f"Transcripción completa guardada en: {transcription_file}")
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
        """Procesar una URL individual"""
        try:
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"Procesando URL {i}/{total_urls}: {url}")
            print(f"\n[INFO] Procesando URL {i}/{total_urls}: {url}")
            
            # Verificar checkpoint
            checkpoint_status = self._get_checkpoint_status(url)
            
            # 1. Descarga
            if 'download' not in checkpoint_status:
                self.logger.info("ETAPA 1: Descarga de video")
                print("[INFO] ETAPA 1: Descarga de video")
                
                file_path = self.download_video(url)
                if not file_path:
                    raise Exception("No se pudo descargar el video con ningún método")
                    
                self._save_checkpoint(url, 'download', 'completed')
            else:
                self.logger.info("Descarga ya completada, saltando...")
                print("[INFO] Descarga ya completada, saltando...")
                file_path = self._find_audio_file(url)
                if not file_path:
                    raise Exception("No se encontró el archivo de audio descargado")
            
            # 2. Transcripción
            if 'transcription' not in checkpoint_status:
                self.logger.info("ETAPA 2: Transcripción")
                print("[INFO] ETAPA 2: Transcripción")
                
                transcription_file = self.transcribe_video(file_path)
                if not transcription_file:
                    raise Exception("No se pudo transcribir el video")
                    
                self._save_checkpoint(url, 'transcription', 'completed')
            else:
                self.logger.info("Transcripción ya completada, saltando...")
                print("[INFO] Transcripción ya completada, saltando...")
                transcription_file = self._find_transcription_file(url)
                if not transcription_file:
                    raise Exception("No se encontró el archivo de transcripción")
            
            # 3. Resumen
            if 'summary' not in checkpoint_status:
                self.logger.info("ETAPA 3: Generación de resumen")
                print("[INFO] ETAPA 3: Generación de resumen")
                
                summary_files = self.summarize_transcription(transcription_file)
                if not summary_files:
                    raise Exception("No se pudo generar el resumen")
                    
                self._save_checkpoint(url, 'summary', 'completed')
            else:
                self.logger.info("Resumen ya completado, saltando...")
                print("[INFO] Resumen ya completado, saltando...")
                summary_files = self._find_summary_files(url)
                if not summary_files:
                    raise Exception("No se encontraron los archivos de resumen")
            
            # Registrar uso
            self._log_usage(url)
            
            self.logger.info(f"Proceso completado para: {url}")
            print(f"[INFO] Proceso completado para: {url}")
            
        except Exception as e:
            error_msg = f"Error procesando {url}: {str(e)}"
            self.logger.error(error_msg)
            print(f"\n[ERROR] {error_msg}")
            # Guardar el error en el checkpoint
            self._save_checkpoint(url, 'error', str(e))
            # No lanzar la excepción para continuar con las siguientes URLs
            return False
            
        return True

    def _find_audio_file(self, url):
        """Find downloaded audio file for URL in the downloads directory"""
        try:
            # First try to find by exact match
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = self._sanitize_filename(info['title'])
                expected_file = os.path.join(self.output_dir, f"{title}.mp3")
                if os.path.exists(expected_file):
                    self.logger.info(f"Archivo encontrado por coincidencia exacta: {expected_file}")
                    return expected_file
                
            # If not found, try to find by video ID
            video_id = url.split('watch?v=')[-1].split('&')[0]
            for file in os.listdir(self.output_dir):
                if file.endswith('.mp3'):
                    file_path = os.path.join(self.output_dir, file)
                    # Check if it's the most recently modified file
                    if os.path.getmtime(file_path) > datetime.now().timestamp() - 60:  # File modified in the last minute
                        self.logger.info(f"Archivo encontrado por tiempo de modificación reciente: {file_path}")
                        return file_path
                    
            # If still not found, try to find by partial title match
            for file in os.listdir(self.output_dir):
                if file.endswith('.mp3'):
                    # Try matching by first 20 chars of sanitized title
                    if title and title[:20].lower() in file.lower():
                        file_path = os.path.join(self.output_dir, file)
                        self.logger.info(f"Archivo encontrado por coincidencia parcial: {file_path}")
                        return file_path
                    
            raise FileNotFoundError(f"No se encontró el archivo de audio para: {url}")
        except Exception as e:
            self.logger.error(f"Error buscando archivo de audio: {str(e)}")
            raise

    def _find_transcription_file(self, url):
        """Find transcription file for URL in the transcriptions directory"""
        try:
            audio_file = self._find_audio_file(url)
            base_name = os.path.splitext(os.path.basename(audio_file))[0]
            expected_file = os.path.join(self.transcriptions_dir, f"{base_name}.txt")
            
            if os.path.exists(expected_file):
                return expected_file
                
            raise FileNotFoundError(f"No se encontró el archivo de transcripción para: {url}")
        except Exception as e:
            self.logger.error(f"Error buscando archivo de transcripción: {str(e)}")
            raise

    def _find_summary_files(self, url):
        """Find summary files for URL in the summaries directory"""
        try:
            transcription_file = self._find_transcription_file(url)
            base_name = os.path.splitext(os.path.basename(transcription_file))[0]
            expected_files = [os.path.join(self.summaries_dir, f"{base_name}_summary_es.txt"), os.path.join(self.summaries_dir, f"{base_name}_summary_en.txt")]
            
            if all(os.path.exists(file) for file in expected_files):
                return expected_files
                
            raise FileNotFoundError(f"No se encontraron los archivos de resumen para: {url}")
        except Exception as e:
            self.logger.error(f"Error buscando archivos de resumen: {str(e)}")
            raise

    def download_from_file(self, file_path):
        """
        Descarga videos desde un archivo de URLs, transcribe y resume
        
        Args:
            file_path (str): Ruta al archivo con URLs (una por línea)
            
        Returns:
            list: Lista de rutas a los archivos de resumen
        """
        self.logger.info(f"\n{'='*50}")
        self.logger.info("INICIO DEL PROCESO")
        self.logger.info(f"{'='*50}")
        
        if not os.path.exists(file_path):
            error_msg = f"El archivo no existe: {file_path}"
            self.logger.error(error_msg)
            print(f"\n[ERROR] {error_msg}")
            return []
            
        summary_files = []
        failed_urls = []
        
        try:
            # Leer URLs
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
                
            total_urls = len(urls)
            self.logger.info(f"Total de URLs a procesar: {total_urls}")
            print(f"\n[INFO] Total de URLs a procesar: {total_urls}")
            
            # Procesar cada URL
            for i, url in enumerate(urls, 1):
                try:
                    if self.process_url(url, i, total_urls):
                        summary_files.append(url)
                    else:
                        failed_urls.append(url)
                except Exception as e:
                    error_msg = f"Error al procesar URL {i}/{total_urls}: {str(e)}"
                    self.logger.error(error_msg)
                    print(f"\n[ERROR] {error_msg}")
                    failed_urls.append(url)
                    
            # Resumen final
            self.logger.info(f"\n{'='*50}")
            self.logger.info("RESUMEN FINAL DEL PROCESO")
            self.logger.info(f"{'='*50}")
            self.logger.info(f"Total URLs procesadas: {total_urls}")
            self.logger.info(f"Procesamientos exitosos: {len(summary_files)}")
            self.logger.info(f"Procesamientos fallidos: {len(failed_urls)}")
            
            print(f"\n[INFO] {'='*50}")
            print(f"[INFO] RESUMEN FINAL DEL PROCESO")
            print(f"[INFO] {'='*50}")
            print(f"[INFO] Total URLs procesadas: {total_urls}")
            print(f"[INFO] Procesamientos exitosos: {len(summary_files)}")
            print(f"[INFO] Procesamientos fallidos: {len(failed_urls)}")
            
            if failed_urls:
                self.logger.warning("\nURLs que fallaron:")
                print("\n[WARNING] URLs que fallaron:")
                for url in failed_urls:
                    self.logger.warning(f"- {url}")
                    print(f"[WARNING] - {url}")
                    
            return summary_files
            
        except Exception as e:
            error_msg = f"Error general en el proceso: {str(e)}"
            self.logger.error(error_msg)
            print(f"\n[ERROR] {error_msg}")
            return summary_files

if __name__ == "__main__":
    downloader = YouTubeDownloader()
    downloader.download_from_file('urls.txt')
    downloader._delete_duplicates() 