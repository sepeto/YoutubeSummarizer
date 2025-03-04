import os
import whisper
import logging
from datetime import datetime

class WhisperTranscriber:
    def __init__(self, model_size='base', output_dir='output/transcriptions'):
        self.model_size = model_size
        self.output_dir = output_dir
        self.model = None
        self._setup_logging()
        self._ensure_output_dir()
        
    def _setup_logging(self):
        """Configurar logging específico para el transcriptor"""
        self.logger = logging.getLogger('transcriber')
        self.logger.setLevel(logging.INFO)
        
        # Crear el directorio de logs si no existe
        log_dir = 'output/logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Handler para archivo
        log_file = os.path.join(log_dir, f'transcribe_{datetime.now().strftime("%Y%m%d")}.log')
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
            self.logger.info(f"Directorio de transcripciones creado: {self.output_dir}")
            
    def _load_model(self):
        """Cargar el modelo de Whisper"""
        if self.model is None:
            self.logger.info(f"Cargando modelo Whisper ({self.model_size})...")
            try:
                self.model = whisper.load_model(self.model_size)
                self.logger.info("Modelo cargado correctamente")
            except Exception as e:
                self.logger.error(f"Error al cargar el modelo: {str(e)}")
                raise
                
    def transcribe_audio(self, audio_path):
        """
        Transcribe un archivo de audio usando Whisper
        
        Args:
            audio_path (str): Ruta al archivo de audio
            
        Returns:
            tuple: (ruta_transcripcion, texto_transcrito)
        """
        self.logger.info(f"Iniciando transcripción: {audio_path}")
        
        try:
            # Verificar que el archivo existe
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"No se encuentra el archivo de audio: {audio_path}")
                
            # Cargar modelo si no está cargado
            self._load_model()
            
            # Obtener nombre base del archivo
            base_name = os.path.basename(audio_path)
            file_name = os.path.splitext(base_name)[0]
            
            # Transcribir audio
            self.logger.info("Transcribiendo audio...")
            result = self.model.transcribe(audio_path)
            transcription = result["text"]
            
            # Guardar transcripción
            output_path = os.path.join(self.output_dir, f"{file_name}.txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(transcription)
                
            self.logger.info(f"Transcripción completada y guardada en: {output_path}")
            return output_path, transcription
            
        except Exception as e:
            self.logger.error(f"Error al transcribir {audio_path}: {str(e)}")
            raise
            
    def transcribe_multiple(self, audio_files):
        """
        Transcribe múltiples archivos de audio
        
        Args:
            audio_files (list): Lista de rutas a archivos de audio
            
        Returns:
            list: Lista de diccionarios con información de las transcripciones
        """
        results = []
        failed_files = []
        
        total_files = len(audio_files)
        self.logger.info(f"Procesando {total_files} archivos de audio")
        
        for i, audio_file in enumerate(audio_files, 1):
            try:
                self.logger.info(f"\nProcesando archivo {i}/{total_files}: {audio_file}")
                output_path, transcription = self.transcribe_audio(audio_file)
                
                results.append({
                    'audio_file': audio_file,
                    'transcription_file': output_path,
                    'transcription_text': transcription
                })
                
                self.logger.info(f"Archivo {i}/{total_files} procesado correctamente")
                
            except Exception as e:
                self.logger.error(f"Error al procesar archivo {i}/{total_files}: {str(e)}")
                failed_files.append(audio_file)
                
        # Resumen final
        success_count = len(results)
        failed_count = len(failed_files)
        
        self.logger.info("\n=== RESUMEN DE TRANSCRIPCIONES ===")
        self.logger.info(f"Total archivos procesados: {total_files}")
        self.logger.info(f"Transcripciones exitosas: {success_count}")
        self.logger.info(f"Transcripciones fallidas: {failed_count}")
        
        if failed_files:
            self.logger.warning("\nArchivos que fallaron:")
            for file in failed_files:
                self.logger.warning(f"- {file}")
                
        return results 