"""
Models for transcription and summarization
"""
import os
from openai import OpenAI
from . import config
import openai

class Transcriber:
    @staticmethod
    def get_transcriber():
        if config.TRANSCRIPTION_METHOD == "local":
            return LocalWhisperTranscriber()
        elif config.TRANSCRIPTION_METHOD == "api":
            return APIWhisperTranscriber()
        else:
            raise ValueError(f"Invalid transcription method: {config.TRANSCRIPTION_METHOD}")

class LocalWhisperTranscriber:
    def __init__(self):
        if not 'whisper' in globals():
            import whisper
        self.model = whisper.load_model(config.WHISPER_MODEL)
    
    def transcribe(self, audio_file):
        result = self.model.transcribe(audio_file)
        return result["text"]

class APIWhisperTranscriber:
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    def transcribe(self, audio_file):
        with open(audio_file, "rb") as f:
            result = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        return result.text

class Summarizer:
    @staticmethod
    def get_summarizer():
        if config.SUMMARIZATION_METHOD == "openai":
            return OpenAISummarizer()
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
        
    def summarize(self, text):
        """Generar resumen usando OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un experto en resumir contenido. Genera un resumen detallado y bien estructurado del texto proporcionado."},
                    {"role": "user", "content": f"Resume el siguiente texto:\n\n{text}"}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[ERROR] Error generando resumen con OpenAI: {str(e)}")
            return None
            
    def translate(self, text, target_lang='es'):
        """Traducir texto usando OpenAI"""
        try:
            lang_name = "español" if target_lang == 'es' else "inglés"
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"Eres un experto traductor. Traduce el texto al {lang_name} manteniendo el significado y el tono original."},
                    {"role": "user", "content": f"Traduce el siguiente texto al {lang_name}:\n\n{text}"}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[ERROR] Error traduciendo con OpenAI: {str(e)}")
            return None 