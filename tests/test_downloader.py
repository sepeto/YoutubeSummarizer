import os
import shutil
import unittest
import asyncio
from utils.downloader import YoutubeDownloader

class TestDownloader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create test directories"""
        cls.test_dir = "test_downloads"
        cls.test_url = "https://www.youtube.com/watch?v=OZaxtm3RyCw"
        os.makedirs(cls.test_dir, exist_ok=True)
        cls.downloader = YoutubeDownloader(cls.test_dir)

    def setUp(self):
        """Clean test directory before each test"""
        for file in os.listdir(self.test_dir):
            file_path = os.path.join(self.test_dir, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)

    @classmethod
    def tearDownClass(cls):
        """Remove test directory after all tests"""
        shutil.rmtree(cls.test_dir)

    def test_download_video(self):
        """Test video download functionality"""
        # Download video
        filename = asyncio.run(self.downloader.download_url(self.test_url))
        self.assertIsNotNone(filename, "Download should succeed")
        self.assertTrue(os.path.exists(filename), "File should exist")
        self.assertTrue(os.path.getsize(filename) > 0, "File should have content")

    def test_download_invalid_url(self):
        """Test handling of invalid URL"""
        filename = asyncio.run(self.downloader.download_url("https://www.youtube.com/watch?v=invalid"))
        self.assertIsNone(filename, "Should fail with invalid URL")

    def test_download_from_file(self):
        """Test downloading from file"""
        # Create test file
        test_file = os.path.join(self.test_dir, "test_urls.txt")
        with open(test_file, "w") as f:
            f.write(self.test_url)

        # Download videos
        results = asyncio.run(self.downloader.download_from_file(test_file))
        self.assertTrue(len(results['success']) > 0, "Should have successful downloads")
        self.assertEqual(len(results['failed']), 0, "Should have no failed downloads")

        # Verify files exist
        for filename in results['success']:
            self.assertTrue(os.path.exists(filename), f"File {filename} should exist")
            self.assertTrue(os.path.getsize(filename) > 0, f"File {filename} should have content")

if __name__ == '__main__':
    unittest.main() 