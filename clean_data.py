import os
import shutil
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def clean_folder(folder_path: str) -> None:
    """Clean all contents of a folder if it exists."""
    try:
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            os.makedirs(folder_path)
            logging.info(f"✨ Cleaned folder: {folder_path}")
        else:
            os.makedirs(folder_path)
            logging.info(f"📁 Created folder: {folder_path}")
    except Exception as e:
        logging.error(f"❌ Error cleaning {folder_path}: {str(e)}")

def main():
    """Main function to clean all data folders."""
    folders_to_clean = [
        "videos",
        "audio",
        "transcripts",
        "summaries"
    ]
    
    logging.info("🧹 Starting cleanup process...")
    
    for folder in folders_to_clean:
        clean_folder(folder)
    
    logging.info("✅ Cleanup completed!")

if __name__ == "__main__":
    main() 