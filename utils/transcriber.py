import os
import logging
import openai
from moviepy.editor import AudioFileClip
from typing import Dict, List, Tuple
from dotenv import load_dotenv

class Transcriber:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.max_chunk_size = 24 * 1024 * 1024  # 24MB para estar seguros
        
    def transcribe_audio(self, audio_path: str) -> tuple[bool, str]:
        """Transcribe an audio file."""
        try:
            # Verificar si ya existe una transcripción válida
            output_path = os.path.join(self.output_dir, os.path.splitext(os.path.basename(audio_path))[0] + '.txt')
            if os.path.exists(output_path):
                self.logger.info(f"Valid transcription exists: {output_path}")
                return True, output_path
                
            self.logger.info(f"Transcribing {audio_path}")
            
            # Verificar tamaño del archivo
            file_size = os.path.getsize(audio_path)
            if file_size > self.max_chunk_size:
                return self._transcribe_large_file(audio_path)
            
            # Transcribir archivo completo
            with open(audio_path, 'rb') as audio_file:
                response = openai.Audio.transcribe(
                    "whisper-1",
                    audio_file
                )
                
            if not response or not response.get('text'):
                self.logger.error(f"No transcription generated for {audio_path}")
                return False, ""
                
            # Guardar transcripción
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(response['text'])
                
            self.logger.info(f"Successfully transcribed to {output_path}")
            return True, output_path
            
        except Exception as e:
            self.logger.error(f"Failed to transcribe {audio_path}: {str(e)}")
            return False, ""
            
    def _transcribe_large_file(self, audio_path: str) -> tuple[bool, str]:
        """Transcribe a large audio file by splitting it into chunks."""
        try:
            # Cargar audio
            audio = AudioFileClip(audio_path)
            chunk_duration = 600  # 10 minutos en segundos
            total_duration = audio.duration
            chunks = []
            
            # Dividir en chunks
            for start_time in range(0, int(total_duration), chunk_duration):
                end_time = min(start_time + chunk_duration, total_duration)
                chunk = audio.subclip(start_time, end_time)
                chunk_path = f"{audio_path}_chunk_{start_time//chunk_duration}.mp3"
                chunk.write_audiofile(chunk_path)
                chunks.append(chunk_path)
                
            # Cerrar el clip de audio
            audio.close()
                
            # Transcribir cada chunk
            transcriptions = []
            for chunk_path in chunks:
                try:
                    with open(chunk_path, 'rb') as audio_file:
                        response = openai.Audio.transcribe(
                            "whisper-1",
                            audio_file
                        )
                        if response and response.get('text'):
                            transcriptions.append(response['text'])
                except Exception as e:
                    self.logger.error(f"Failed to transcribe chunk {chunk_path}: {str(e)}")
                finally:
                    # Limpiar chunk
                    if os.path.exists(chunk_path):
                        os.remove(chunk_path)
                        
            if not transcriptions:
                return False, ""
                
            # Combinar transcripciones
            output_path = os.path.join(self.output_dir, os.path.splitext(os.path.basename(audio_path))[0] + '.txt')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n\n".join(transcriptions))
                
            self.logger.info(f"Successfully transcribed large file to {output_path}")
            return True, output_path
            
        except Exception as e:
            self.logger.error(f"Failed to transcribe large file {audio_path}: {str(e)}")
            return False, ""
            
    def _format_transcription(self, text: str) -> str:
        """Format transcription with proper punctuation and paragraphs."""
        try:
            # Use OpenAI to format the text
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that formats text with proper punctuation and paragraphs."},
                    {"role": "user", "content": f"Please format this transcription with proper punctuation and paragraphs. Keep the exact same words but make it more readable:\n\n{text}"}
                ],
                temperature=0.3,  # Lower temperature for more consistent formatting
                max_tokens=2000
            )
            
            formatted_text = response.choices[0].message.content
            return formatted_text if formatted_text else text
            
        except Exception as e:
            self.logger.warning(f"Failed to format transcription, using original: {str(e)}")
            return text
            
    def batch_transcribe(self, audio_files: List[str]) -> Dict[str, List[str]]:
        """Transcribes multiple audio files"""
        results = {
            'success': [],
            'failed': []
        }
        
        for audio_path in audio_files:
            if not os.path.exists(audio_path):
                self.logger.error(f"Audio file not found: {audio_path}")
                results['failed'].append(audio_path)
                continue
                
            success, output_path = self.transcribe_audio(audio_path)
            if success:
                results['success'].append(output_path)
            else:
                results['failed'].append(audio_path)
                
        self.logger.info(f"Transcription complete. Success: {len(results['success'])}, Failed: {len(results['failed'])}")
        return results 