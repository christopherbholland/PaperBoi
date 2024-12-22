import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from datetime import datetime

class PaperProcessor:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Set up base directory (current directory)
        self.base_dir = Path.cwd()
        
        # Define directory names
        self.directories = {
            'papers': self.base_dir / 'full_papers',
            'summaries': self.base_dir / 'paperboi_summaries',
            'metadata': self.base_dir / 'metadata',
            'errors': self.base_dir / 'error_log'
        }
        
        # Create directories if they don't exist
        self._create_directories()
        
        # Set up logging
        self._setup_logging()
        
    def _create_directories(self):
        """Create necessary directories if they don't exist."""
        for dir_path in self.directories.values():
            dir_path.mkdir(exist_ok=True)
            
    def _setup_logging(self):
        """Configure logging to file and console."""
        log_file = self.directories['errors'] / f'error_log_{datetime.now().strftime("%Y%m%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
    def process_paper(self, url: str):
        """
        Main method to process a paper from URL.
        
        Args:
            url (str): URL of the PDF to process
        """
        try:
            logging.info(f"Starting to process paper from URL: {url}")
            # TODO: Implement URL validation and PDF download
            
        except Exception as e:
            logging.error(f"Error processing paper from URL {url}: {str(e)}")
            raise

if __name__ == "__main__":
    # Example usage
    processor = PaperProcessor()
    # Test URL to be added
    # processor.process_paper("https://example.com/paper.pdf")