"""
Configuration file for YouTubeDownloader
Contains API keys and switches for different transcription/summarization methods
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI API Key - Load from environment variable
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Transcription Settings
TRANSCRIPTION_METHOD = "api"  # Current: "api"
# Available Transcription Methods:
# - "local": Use local Whisper model
# - "api": Use OpenAI Whisper API

# Whisper Models (for local transcription):
# - "tiny": Fastest, lowest accuracy
# - "base": Good balance of speed/accuracy
# - "small": Better accuracy, slower
# - "medium": Even better accuracy, much slower
# - "large": Best accuracy, very slow
WHISPER_MODEL = "base"

# Summarization Settings
SUMMARIZATION_METHOD = "openai"  # Current: "openai"
# Available Summarization Methods:
# - "openai": Use OpenAI GPT models
# - "llama": Use local Llama model
# - "gpt4allmini": Use local GPT4All-mini model

# OpenAI Models:
# - "gpt-4": Most capable model
# - "gpt-4-turbo-preview": Latest GPT-4 with larger context
# - "gpt-3.5-turbo": Fast and cost-effective
OPENAI_MODEL = "gpt-3.5-turbo"

# Local Model Paths
LLAMA_MODEL_PATH = "models/llama-2-7b-chat.ggmlv3.q4_0.bin"
GPT4ALL_MODEL_PATH = "models/gpt4all-mini.bin"

# Model Parameters
LLAMA_PARAMS = {
    "max_tokens": 500,
    "temperature": 0.7,
    "top_p": 0.95
}

GPT4ALL_PARAMS = {
    "max_tokens": 500,
    "temperature": 0.7,
    "top_p": 0.95
} 