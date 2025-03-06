"""
Configuration file for YouTubeDownloader
Contains API keys and switches for different transcription/summarization methods
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('config')

# Load environment variables
load_dotenv()

# OpenAI API Key - Load from environment variable
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Verificar claves API y ajustar métodos si no están disponibles
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY no encontrada en variables de entorno. Cambiando a métodos locales.")
    DEFAULT_TRANSCRIPTION_METHOD = "local"
    DEFAULT_SUMMARIZATION_METHOD = "llama" if ANTHROPIC_API_KEY else "local"
else:
    DEFAULT_TRANSCRIPTION_METHOD = "api"
    DEFAULT_SUMMARIZATION_METHOD = "openai"

if not ANTHROPIC_API_KEY and DEFAULT_SUMMARIZATION_METHOD == "claude":
    logger.warning("ANTHROPIC_API_KEY no encontrada en variables de entorno. Cambiando a OpenAI para resúmenes.")
    DEFAULT_SUMMARIZATION_METHOD = "openai" if OPENAI_API_KEY else "local"

# Base Directories
BASE_DIR = 'output'
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'downloads')
TRANSCRIPTION_DIR = os.path.join(BASE_DIR, 'transcriptions')
SUMMARY_DIR = os.path.join(BASE_DIR, 'summaries')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
COMPRESSED_DIR = os.path.join(BASE_DIR, 'compressed')

# Cache Settings
ENABLE_CACHE = True
CACHE_EXPIRY_DAYS = 30  # Cache expiry in days

# Parallel Processing
ENABLE_PARALLEL = True
MAX_WORKERS = 4  # Maximum number of parallel workers

# Rate Limiting
ENABLE_RATE_LIMITING = True
# Rate limits (requests per minute)
YOUTUBE_RATE_LIMIT = 60
OPENAI_RATE_LIMIT = 20
ANTHROPIC_RATE_LIMIT = 20

# Retry Settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Transcription Settings
TRANSCRIPTION_METHOD = DEFAULT_TRANSCRIPTION_METHOD
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
SUMMARIZATION_METHOD = DEFAULT_SUMMARIZATION_METHOD
# Available Summarization Methods:
# - "openai": Use OpenAI GPT models
# - "claude": Use Anthropic Claude models
# - "llama": Use local Llama model
# - "gpt4allmini": Use local GPT4All-mini model

# OpenAI Models:
# - "gpt-4": Most capable model
# - "gpt-4-turbo-preview": Latest GPT-4 with larger context
# - "gpt-3.5-turbo": Fast and cost-effective
OPENAI_MODEL = "gpt-3.5-turbo"

# Claude Models:
# - "claude-3-opus-20240229": Most capable Claude model
# - "claude-3-sonnet-20240229": Good balance of capability and cost
# - "claude-3-haiku-20240307": Fast and cost-effective
CLAUDE_MODEL = "claude-3-sonnet-20240229"

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

# Compression Settings
ENABLE_COMPRESSION = True
COMPRESSION_FORMAT = "zip"  # Options: "zip", "tar.gz"
COMPRESSION_LEVEL = 6  # 1-9, higher is more compression but slower

# Verificar dependencias críticas
def check_dependencies():
    missing_deps = []
    
    # Verificar ffmpeg (necesario para procesamiento de audio)
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode != 0:
            missing_deps.append("ffmpeg")
    except Exception:
        missing_deps.append("ffmpeg")
    
    # Verificar dependencias de Python
    try:
        import yt_dlp
    except ImportError:
        missing_deps.append("yt-dlp")
    
    try:
        import pytube
    except ImportError:
        missing_deps.append("pytube")
    
    try:
        import pydub
    except ImportError:
        missing_deps.append("pydub")
    
    if TRANSCRIPTION_METHOD == "local":
        try:
            import whisper
        except ImportError:
            missing_deps.append("whisper")
    
    if missing_deps:
        logger.warning(f"Dependencias faltantes: {', '.join(missing_deps)}")
        print(f"[ADVERTENCIA] Faltan las siguientes dependencias: {', '.join(missing_deps)}")
        print("Instale las dependencias faltantes con: pip install <nombre_dependencia>")
        
    return missing_deps

# Ejecutar verificación de dependencias al importar
MISSING_DEPENDENCIES = check_dependencies()

# Notification Settings
ENABLE_NOTIFICATIONS = False
NOTIFICATION_EMAIL = os.getenv('NOTIFICATION_EMAIL', '')
SMTP_SERVER = os.getenv('SMTP_SERVER', '')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')

# URL Validation
VALIDATE_URLS = True
ALLOW_PLAYLISTS = True
MAX_VIDEOS_PER_PLAYLIST = 10

# Backup Settings
ENABLE_AUTO_BACKUP = True
BACKUP_FREQUENCY = 24  # hours
MAX_BACKUPS = 5  # Maximum number of backups to keep

# Resource Monitoring
ENABLE_RESOURCE_MONITORING = True
MAX_DISK_USAGE_PERCENT = 90
MAX_MEMORY_USAGE_PERCENT = 80