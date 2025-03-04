"""
Models for transcription and summarization
"""
import os
from openai import OpenAI
from . import config

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

class OpenAISummarizer:
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    def summarize(self, text):
        response = self.client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates concise summaries of transcribed content. Format your response in two sections:\n1. TAGLINES: Bullet points of key topics and main teachings\n2. SUMMARY: A brief overview of the content"},
                {"role": "user", "content": f"Please analyze this transcription and provide taglines and summary:\n\n{text}"}
            ]
        )
        return response.choices[0].message.content 