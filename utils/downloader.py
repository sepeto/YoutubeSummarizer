import os
import logging
import asyncio
import yt_dlp
from pytube import YouTube
from typing import List, Dict, Optional
import subprocess
import sys
import re
import yaml
from .logger import Logger
from dotenv import load_dotenv

class YoutubeDownloader:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config()
        self._ensure_dependencies()
        os.makedirs(output_dir, exist_ok=True)
    
    def _load_config(self) -> dict:
        """Carga la configuración desde config.yaml"""
        try:
            with open("config.yaml", 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config['download']
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            return {
                'type': 'video',
                'video_quality': 'highest',
                'audio_format': 'mp3',
                'audio_quality': 320,
                'output_dir': 'Descargas'
            }
    
    def _ensure_dependencies(self):
        """Asegura que las dependencias estén instaladas y actualizadas"""
        try:
            # Actualizar yt-dlp
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"], 
                         capture_output=True, check=True)
            self.logger.info("yt-dlp updated successfully")
        except Exception as e:
            self.logger.warning(f"Could not update yt-dlp: {str(e)}")
            
        try:
            # Actualizar pytube como respaldo
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pytube"], 
                         capture_output=True, check=True)
            self.logger.info("pytube updated successfully")
        except Exception as e:
            self.logger.warning(f"Could not update pytube: {str(e)}")
    
    def _extract_urls(self, file_path: str) -> List[str]:
        """Extrae URLs de YouTube de un archivo de texto"""
        urls = []
        url_pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+'
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                matches = re.finditer(url_pattern, content)
                urls = [match.group() for match in matches]
            
            self.logger.info(f"Found {len(urls)} valid YouTube URLs in {file_path}")
            return urls
        except Exception as e:
            self.logger.error(f"Error reading URLs from file: {str(e)}")
            return []
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',  # URLs normales y compartidas
            r'youtu\.be\/([0-9A-Za-z_-]{11})',   # URLs cortas
            r'embed\/([0-9A-Za-z_-]{11})'        # URLs de embed
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
                
        return None
    
    async def download_url(self, url: str) -> tuple[str, str]:
        """Downloads a video from a URL and returns (file_path, title)"""
        try:
            # Extract video ID
            video_id = self._extract_video_id(url)
            if not video_id:
                self.logger.error(f"Invalid YouTube URL: {url}")
                return None, None
                
            self.logger.info(f"Downloading {url}")
            
            # Configure yt-dlp
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True
            }
            
            # Get video info first
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                filename = ydl.prepare_filename(info)
                title = info.get('title', '')
                
                # Check if file already exists
                if os.path.exists(filename):
                    self.logger.info(f"Video already exists: {filename}")
                    return filename, title
                    
                # Download video
                self.logger.info(f"Downloading to {filename}")
                ydl.download([url])
                
                if os.path.exists(filename):
                    self.logger.info(f"Successfully downloaded {filename}")
                    return filename, title
                    
            return None, None
            
        except Exception as e:
            self.logger.error(f"Failed to download {url}: {str(e)}")
            return None, None

    async def download_from_file(self, urls_file: str) -> Dict[str, List[str]]:
        """Downloads videos from a file containing URLs"""
        results = {
            'success': [],
            'failed': []
        }
        
        try:
            with open(urls_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
                
        except Exception as e:
            self.logger.error(f"Failed to read URLs file: {str(e)}")
            return results
            
        for url in urls:
            filename, title = await self.download_url(url)
            if filename:
                results['success'].append((filename, title))
            else:
                results['failed'].append((url, None))
                
        self.logger.info(f"Download complete. Success: {len(results['success'])}, Failed: {len(results['failed'])}")
        return results

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be safe for all operating systems"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '')
            
        # Replace spaces and dots with underscores
        filename = filename.replace(' ', '_').replace('.', '_')
        
        # Remove any non-ASCII characters
        filename = ''.join(c for c in filename if ord(c) < 128)
        
        # Limit length
        max_length = 200
        if len(filename) > max_length:
            filename = filename[:max_length]
            
        return filename.strip('_') 