import asyncio
import sys
from utils.downloader import YoutubeDownloader
from utils.logger import Logger

async def main():
    logger = Logger("main")
    downloader = YoutubeDownloader()
    
    if len(sys.argv) < 2:
        logger.error("Please provide a URL or a file containing URLs")
        print("\nUsage:")
        print("Single URL: python download_videos.py https://youtube.com/watch?v=...")
        print("Multiple URLs from file: python download_videos.py urls.txt")
        return
    
    input_path = sys.argv[1]
    
    if input_path.startswith(('http://', 'https://', 'www.', 'youtube.com', 'youtu.be')):
        # Single URL
        success = await downloader.download_url(input_path)
        if success:
            logger.info("Download completed successfully")
        else:
            logger.error("Download failed")
    else:
        # File with URLs
        await downloader.download_from_file(input_path)

if __name__ == "__main__":
    asyncio.run(main()) 