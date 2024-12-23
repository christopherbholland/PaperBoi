import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import logging
from datetime import datetime
import requests
from urllib.parse import urlparse
import re
from typing import Tuple, Optional

class PaperProcessor:
    def __init__(self):
        """
        Initialize the PaperProcessor with necessary directories and logging setup.
        Creates required directories if they don't exist and configures logging.
        """
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
        """
        Create necessary directories if they don't exist.
        Creates directories for papers, summaries, metadata, and error logs.
        """
        for dir_path in self.directories.values():
            dir_path.mkdir(exist_ok=True)
            
    def _setup_logging(self):
        """
        Configure logging to file and console.
        Sets up logging with timestamp, level, and message format.
        Logs are written to both a file and displayed in console.
        """
        log_file = self.directories['errors'] / f'error_log_{datetime.now().strftime("%Y%m%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

    def _validate_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if the URL is properly formatted and points to a PDF.
        
        Args:
            url (str): URL to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
                - First element is True if URL is valid, False otherwise
                - Second element contains error message if URL is invalid, None otherwise
        """
        try:
            # Check if URL is properly formatted
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                return False, "Invalid URL format"
            
            # Follow redirects and get final URL
            response = requests.head(url, allow_redirects=True)
            final_url = response.url
            
            # Check if content type is PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'application/pdf' not in content_type:
                return False, f"URL does not point to a PDF (content-type: {content_type})"
            
            return True, None
            
        except requests.RequestException as e:
            return False, f"Error validating URL: {str(e)}"

    def _download_pdf(self, url: str) -> Optional[Path]:
        """
        Download PDF from URL and save to papers directory.
        
        Args:
            url (str): URL of the PDF to download
            
        Returns:
            Optional[Path]: Path to downloaded file if successful, None otherwise
        """
        try:
            # Generate filename from timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"paper_{timestamp}.pdf"
            file_path = self.directories['papers'] / filename
            
            # Download the file
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Save the file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logging.info(f"Successfully downloaded PDF to {file_path}")
            return file_path
            
        except Exception as e:
            logging.error(f"Error downloading PDF: {str(e)}")
            return None

    def process_paper(self, url: str):
        """
        Main method to process a paper from URL.
        
        Args:
            url (str): URL of the PDF to process
            
        Raises:
            ValueError: If the URL is invalid
            RuntimeError: If PDF download fails
            Exception: For other unexpected errors
        """
        try:
            logging.info(f"Starting to process paper from URL: {url}")
            
            # Validate URL
            is_valid, error_message = self._validate_url(url)
            if not is_valid:
                raise ValueError(f"Invalid URL: {error_message}")
            
            # Download PDF
            pdf_path = self._download_pdf(url)
            if not pdf_path:
                raise RuntimeError("Failed to download PDF")
            
            # TODO: Next steps - PDF text extraction and processing
            
        except Exception as e:
            logging.error(f"Error processing paper from URL {url}: {str(e)}")
            raise

if __name__ == "__main__":
    # Example usage
    processor = PaperProcessor()
    # Test with a real PDF URL
    # processor.process_paper("https://example.com/paper.pdf")