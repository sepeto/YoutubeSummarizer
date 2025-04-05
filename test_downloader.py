import asyncio
import logging
from utils.downloader import YoutubeDownloader

logging.basicConfig(level=logging.INFO)

async def main():
    downloader = YoutubeDownloader('videos')
    results = await downloader.download_from_file('test_urls.txt')
    print("\nDownload Results:")
    print(f"Success: {len(results['success'])}")
    print(f"Failed: {len(results['failed'])}")
    print("\nSuccessful downloads:")
    for file in results['success']:
        print(f"- {file}")
    if results['failed']:
        print("\nFailed downloads:")
        for url in results['failed']:
            print(f"- {url}")

if __name__ == "__main__":
    asyncio.run(main()) 