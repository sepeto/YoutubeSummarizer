import logging
from utils.audio_converter import AudioConverter
import os

logging.basicConfig(level=logging.INFO)

def main():
    converter = AudioConverter('audio')
    
    # Get all MP4 files from videos directory
    video_files = [os.path.join('videos', f) for f in os.listdir('videos') if f.endswith('.mp4')]
    
    print(f"\nFound {len(video_files)} videos to convert")
    results = converter.batch_convert(video_files)
    
    print("\nConversion Results:")
    print(f"Success: {len(results['success'])}")
    print(f"Failed: {len(results['failed'])}")
    
    print("\nSuccessful conversions:")
    for file in results['success']:
        print(f"- {file}")
        
    if results['failed']:
        print("\nFailed conversions:")
        for file in results['failed']:
            print(f"- {file}")

if __name__ == "__main__":
    main() 