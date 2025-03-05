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
            file_format = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
            
            # Handler para consola con encoding UTF-8
            console_handler = logging.StreamHandler(sys.stdout)
            console_format = logging.Formatter('[%(levelname)s] %(message)s')
            console_handler.setFormatter(console_format)
            self.logger.addHandler(console_handler)
            
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
        """Procesar una URL individual"""
        try:
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"Procesando URL {i}/{total_urls}: {url}")
            print(f"\n[INFO] Procesando URL {i}/{total_urls}: {url}")
            
            # Verificar checkpoint
            checkpoint_status = self._get_checkpoint_status(url)
            success = True
            error_details = []
            
            # 1. Descarga
            file_path = None
            if 'download' not in checkpoint_status:
                self.logger.info("ETAPA 1: Descarga de video")
                print("[INFO] ETAPA 1: Descarga de video")
                
                try:
                    file_path = self.download_video(url)
                    if file_path:
                        self._save_checkpoint(url, 'download', 'completed')
                    else:
                        error_details.append("Fallo en descarga")
                        success = False
                except Exception as e:
                    error_details.append(f"Error en descarga: {str(e)}")
                    success = False
            else:
                self.logger.info("Descarga ya completada, buscando archivo...")
                try:
                    file_path = self._find_audio_file(url)
                except Exception as e:
                    error_details.append(f"Error buscando archivo: {str(e)}")
                    success = False
            
            # 2. Transcripción
            transcription_file = None
            if success and file_path and 'transcription' not in checkpoint_status:
                self.logger.info("ETAPA 2: Transcripción")
                print("[INFO] ETAPA 2: Transcripción")
                
                try:
                    transcription_file = self.transcribe_video(file_path)
                    if transcription_file:
                        self._save_checkpoint(url, 'transcription', 'completed')
                    else:
                        error_details.append("Fallo en transcripción")
                        success = False
                except Exception as e:
                    error_details.append(f"Error en transcripción: {str(e)}")
                    success = False
            elif success and file_path:
                self.logger.info("Transcripción ya completada, buscando archivo...")
                try:
                    transcription_file = self._find_transcription_file(url)
                except Exception as e:
                    error_details.append(f"Error buscando transcripción: {str(e)}")
                    success = False
            
            # 3. Resumen
            if success and transcription_file and 'summary' not in checkpoint_status:
                self.logger.info("ETAPA 3: Generación de resumen")
                print("[INFO] ETAPA 3: Generación de resumen")
                
                try:
                    summary_files = self.summarize_transcription(transcription_file)
                    if summary_files:
                        self._save_checkpoint(url, 'summary', 'completed')
                    else:
                        error_details.append("Fallo en resumen")
                        success = False
                except Exception as e:
                    error_details.append(f"Error en resumen: {str(e)}")
                    success = False
            elif success and transcription_file:
                self.logger.info("Resumen ya completado, buscando archivos...")
                try:
                    summary_files = self._find_summary_files(url)
                except Exception as e:
                    error_details.append(f"Error buscando resúmenes: {str(e)}")
                    success = False
            
            # Registrar uso si hubo éxito
            if success:
                try:
                    self._log_usage(url)
                except Exception as e:
                    self.logger.error(f"Error registrando uso: {str(e)}")
            
            # Registrar resultado final
            if success:
                self.logger.info(f"Proceso completado para: {url}")
                print(f"[INFO] Proceso completado para: {url}")
            else:
                error_msg = f"Errores procesando {url}: {'; '.join(error_details)}"
                self.logger.error(error_msg)
                print(f"\n[ERROR] {error_msg}")
                self._save_checkpoint(url, 'error', '; '.join(error_details))
            
            return success
            
        except Exception as e:
            error_msg = f"Error crítico procesando {url}: {str(e)}"
            self.logger.error(error_msg)
            print(f"\n[ERROR] {error_msg}")
            self._save_checkpoint(url, 'error', str(e))
            return False

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

    def download_from_file(self, urls_file):
        """Descargar videos desde un archivo de URLs"""
        try:
            # Actualizar dependencias al inicio
            self._update_dependencies()
            
            # Leer URLs del archivo
            if not os.path.exists(urls_file):
                self.logger.error(f"Archivo de URLs no encontrado: {urls_file}")
                print(f"[ERROR] Archivo de URLs no encontrado: {urls_file}")
                return []
                
            with open(urls_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f.readlines() if line.strip()]
                
            if not urls:
                self.logger.warning("No se encontraron URLs en el archivo")
                print("[WARNING] No se encontraron URLs en el archivo")
                return []
                
            self.logger.info(f"Procesando {len(urls)} URLs...")
            print(f"[INFO] Procesando {len(urls)} URLs...")
            
            # Procesar cada URL
            results = []
            for i, url in enumerate(urls, 1):
                try:
                    success = self.process_url(url, i, len(urls))
                    if success:
                        results.append(url)
                except Exception as e:
                    self.logger.error(f"Error procesando URL {url}: {str(e)}")
                    print(f"[ERROR] Error procesando URL {url}: {str(e)}")
                    continue
                    
            # Resumen final
            total = len(urls)
            successful = len(results)
            failed = total - successful
            
            self.logger.info(f"\n{'='*50}")
            self.logger.info("RESUMEN FINAL")
            self.logger.info(f"{'='*50}")
            self.logger.info(f"Total URLs: {total}")
            self.logger.info(f"Exitosas: {successful}")
            self.logger.info(f"Fallidas: {failed}")
            
            print(f"\n{'='*50}")
            print("RESUMEN FINAL")
            print(f"{'='*50}")
            print(f"Total URLs: {total}")
            print(f"Exitosas: {successful}")
            print(f"Fallidas: {failed}")
            
            if failed > 0:
                self.logger.warning("Algunas URLs fallaron. Revise los logs para más detalles.")
                print("\n[WARNING] Algunas URLs fallaron. Revise los logs para más detalles.")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error crítico procesando archivo de URLs: {str(e)}")
            print(f"[ERROR] Error crítico procesando archivo de URLs: {str(e)}")
            return []

    def _get_video_title(self, url):
        """Obtener título del video usando múltiples métodos"""
        try:
            # 1. Intentar con pytube
            from pytube import YouTube
            try:
                yt = YouTube(url)
                return self._sanitize_filename(yt.title)
            except Exception as e:
                self.logger.debug(f"Error obteniendo título con pytube: {str(e)}")
                
            # 2. Intentar con yt-dlp
            try:
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    return self._sanitize_filename(info.get('title', ''))
            except Exception as e:
                self.logger.debug(f"Error obteniendo título con yt-dlp: {str(e)}")
                
            # 3. Usar ID del video como último recurso
            video_id = url.split('watch?v=')[-1].split('&')[0]
            return f"video_{video_id}"
            
        except Exception as e:
            self.logger.error(f"Error obteniendo título del video: {str(e)}")
            return f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

if __name__ == "__main__":
    downloader = YouTubeDownloader()
    downloader.download_from_file('urls.txt')
    downloader._delete_duplicates() 