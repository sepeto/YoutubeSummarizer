# Guía Rápida de Uso

## Scripts Principales

1. Descargar y procesar videos:
```bash
python -m src.downloader
```
Lee URLs de `urls.txt` y genera:
- MP3 en `output/downloads/`
- Transcripciones en `output/transcriptions/`
- Resúmenes (ES/EN) en `output/summaries/`

2. Hacer backup de outputs:
```bash
python backup_output.py
```
Mueve todo el contenido de `output/` a `output_old/backup_[timestamp]/`

## Configuración

En `src/config.py` puedes modificar:

```python
# Método de transcripción
TRANSCRIPTION_METHOD = "openai"  # Opciones: "openai", "whisper-local"

# Método de resumen
SUMMARIZATION_METHOD = "openai"  # Opciones: "openai", "local"

# Modelo OpenAI
OPENAI_MODEL = "gpt-3.5-turbo"  # o "gpt-4" para mejor calidad
```

## Instalación en Nuevo PC

1. Clonar repositorio:
```bash
git clone https://github.com/sepeto/YoutubeSummarizer.git
cd YoutubeSummarizer
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar API keys en `.env`:
```
OPENAI_API_KEY=tu_api_key
```

4. Crear archivo `urls.txt` con URLs de YouTube (una por línea)

## Estructura de Archivos

```
├── src/                  # Código fuente
├── output/              # Archivos generados
│   ├── downloads/      # MP3s
│   ├── transcriptions/ # Textos
│   ├── summaries/     # Resúmenes
│   └── logs/          # Logs
└── output_old/         # Backups antiguos
``` 