import os
import logging
from moviepy.editor import VideoFileClip
from typing import Dict, List

class AudioConverter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        
    def convert_to_mp3(self, video_path: str) -> str:
        """Converts a video file to MP3 and returns the output path"""
        try:
            filename = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(self.output_dir, f"{filename}.mp3")
            
            if os.path.exists(output_path):
                self.logger.info(f"Audio file already exists: {output_path}")
                return output_path
                
            self.logger.info(f"Converting {video_path} to MP3")
            video = VideoFileClip(video_path)
            audio = video.audio
            
            os.makedirs(self.output_dir, exist_ok=True)
            audio.write_audiofile(output_path, logger=None)
            
            audio.close()
            video.close()
            
            self.logger.info(f"Successfully converted to {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to convert {video_path}: {str(e)}")
            return ""
            
    def batch_convert(self, video_files: List[str]) -> Dict[str, List[str]]:
        """Converts multiple video files to MP3"""
        results = {
            'success': [],
            'failed': []
        }
        
        for video_path in video_files:
            if not os.path.exists(video_path):
                self.logger.error(f"Video file not found: {video_path}")
                results['failed'].append(video_path)
                continue
                
            output_path = self.convert_to_mp3(video_path)
            if output_path:
                results['success'].append(output_path)
            else:
                results['failed'].append(video_path)
                
        self.logger.info(f"Conversion complete. Success: {len(results['success'])}, Failed: {len(results['failed'])}")
        return results 