# YouTube Downloader with AI Transcription and Summary

Este proyecto permite descargar videos de YouTube, transcribirlos usando Whisper API y generar resúmenes con GPT-3.5.

## Características

- ✨ Descarga de videos de YouTube usando múltiples métodos (pytube, yt-dlp, youtube-dl)
- 🎯 Transcripción automática usando OpenAI Whisper API
- 📝 Generación de resúmenes y taglines usando GPT-3.5
- 💾 Sistema de checkpoints para continuar procesos interrumpidos
- 📊 Seguimiento de costos de API
- 🔄 Manejo automático de archivos grandes (>25MB)

## Requisitos

- Python 3.8+
- ffmpeg
- OpenAI API Key

## Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/joseba/youtube-downloader.git
cd youtube-downloader
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Configura tu API key de OpenAI en `src/config.py`

## Uso

1. Crea un archivo `urls.txt` con las URLs de YouTube (una por línea)

2. Ejecuta el script:
```bash
python -m src.downloader
```

3. Los archivos generados se guardarán en:
   - MP3: `output/downloads/`
   - Transcripciones: `output/transcriptions/`
   - Resúmenes: `output/summaries/`
   - Logs: `output/logs/`
   - Uso de API: `output/usage_logs/`

## Estructura del Proyecto

```
youtube-downloader/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── downloader.py
│   └── models.py
├── output/
│   ├── downloads/
│   ├── transcriptions/
│   ├── summaries/
│   ├── logs/
│   └── usage_logs/
└── urls.txt
```

## Autor

- Joseba (@joseba)

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles. 