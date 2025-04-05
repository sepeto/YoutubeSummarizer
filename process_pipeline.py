import asyncio
import logging
import os
from utils.downloader import YoutubeDownloader
from utils.audio_converter import AudioConverter
from utils.transcriber import Transcriber
from utils.summarizer import Summarizer

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Directorios
DIRS = {
    'videos': 'videos',
    'audio': 'audio',
    'transcripts': 'transcripts',
    'summaries': 'summaries'
}

# Emojis para el informe
EMOJIS = {
    'success': '✅',
    'error': '❌',
    'skip': '⏭️',
    'process': '⚙️',
    'download': '⬇️',
    'convert': '🔄',
    'transcribe': '📝',
    'summarize': '📋'
}

class Pipeline:
    def __init__(self):
        # Crear directorios si no existen
        for dir_path in DIRS.values():
            os.makedirs(dir_path, exist_ok=True)
            
        # Inicializar componentes
        self.downloader = YoutubeDownloader(DIRS['videos'])
        self.converter = AudioConverter(DIRS['audio'])
        self.transcriber = Transcriber(DIRS['transcripts'])
        self.summarizer = Summarizer(DIRS['summaries'])
        
    async def process_video(self, url: str) -> dict:
        """Procesa un video completo y retorna el estado de cada paso"""
        result = {
            'url': url,
            'title': None,
            'download': {'status': 'pending', 'file': None},
            'convert': {'status': 'pending', 'file': None},
            'transcribe': {'status': 'pending', 'file': None},
            'summarize': {'status': 'pending', 'file': None}
        }
        
        try:
            # 1. Descargar video
            logger.info(f"{EMOJIS['download']} Descargando {url}")
            video_file, video_title = await self.downloader.download_url(url)
            if not video_file:
                result['download']['status'] = 'error'
                return result
            result['download'] = {'status': 'success', 'file': video_file}
            result['title'] = video_title
            
            # 2. Convertir a audio
            logger.info(f"{EMOJIS['convert']} Convirtiendo {video_file}")
            if self.converter.convert_to_mp3(video_file):
                audio_file = os.path.join(DIRS['audio'], os.path.splitext(os.path.basename(video_file))[0] + '.mp3')
                result['convert'] = {'status': 'success', 'file': audio_file}
            else:
                result['convert']['status'] = 'error'
                return result
            
            # 3. Transcribir
            logger.info(f"{EMOJIS['transcribe']} Transcribiendo {audio_file}")
            success, transcript_file = self.transcriber.transcribe_audio(audio_file)
            if not success:
                result['transcribe']['status'] = 'error'
                return result
            result['transcribe'] = {'status': 'success', 'file': transcript_file}
            
            # 4. Resumir
            logger.info(f"{EMOJIS['summarize']} Generando resumen de {transcript_file}")
            with open(transcript_file, 'r', encoding='utf-8') as f:
                text = f.read()
            summary = await self.summarizer.generate_summary(text, os.path.basename(transcript_file))
            if summary:
                result['summarize'] = {'status': 'success', 'file': os.path.join(DIRS['summaries'], os.path.splitext(os.path.basename(transcript_file))[0] + '_summary.txt')}
            else:
                result['summarize']['status'] = 'error'
            
        except Exception as e:
            logger.error(f"Error en el pipeline: {str(e)}")
            
        return result

    def print_report(self, results: list):
        """Imprime un informe formateado de los resultados"""
        print("\n" + "="*50)
        print("📊 INFORME DE PROCESAMIENTO")
        print("="*50 + "\n")
        
        for result in results:
            print(f"🎥 Video: {result['url']}")
            if 'title' in result:
                print(f"📌 Título: {result['title']}")
            print("-"*50)
            
            stages = {
                'download': ('⬇️ Descarga', result.get('download', {}).get('file')),
                'convert': ('🔄 Conversión', result.get('convert', {}).get('file')),
                'transcribe': ('📝 Transcripción', result.get('transcribe', {}).get('file')),
                'summarize': ('📋 Resumen', result.get('summarize', {}).get('file'))
            }
            
            for stage_name, (label, file) in stages.items():
                status = result.get(stage_name, {}).get('status', 'error')
                status_emoji = EMOJIS['success'] if status == 'success' else EMOJIS['error']
                file_path = file or 'N/A'
                print(f"{label}: {status_emoji} {file_path}")
            
            print()  # Línea en blanco entre videos
        
        # Resumen del proceso
        print("="*50)
        print("📈 RESUMEN DEL PROCESO")
        print("="*50)
        
        total = len(results)
        success = sum(1 for r in results if all(r.get(s, {}).get('status') == 'success' for s in ['download', 'convert', 'transcribe', 'summarize']))
        partial = sum(1 for r in results if any(r.get(s, {}).get('status') == 'success' for s in ['download', 'convert', 'transcribe', 'summarize'])) - success
        failed = total - success - partial
        
        print(f"\n🎯 Total de videos procesados: {total}")
        print(f"✅ Completados exitosamente: {success}")
        print(f"⚠️ Completados parcialmente: {partial}")
        print(f"❌ Fallidos: {failed}")
        
        print("\n" + "="*50)

async def main():
    pipeline = Pipeline()
    results = []
    
    # Leer URLs del archivo
    with open('test_urls.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    logger.info(f"{EMOJIS['process']} Iniciando procesamiento de {len(urls)} videos")
    
    for url in urls:
        result = await pipeline.process_video(url)
        results.append(result)
    
    pipeline.print_report(results)

if __name__ == "__main__":
    asyncio.run(main()) 