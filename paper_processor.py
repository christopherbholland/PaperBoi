import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import logging
from datetime import datetime
import requests
from urllib.parse import urlparse
import re
from typing import Tuple, Optional
import pdfplumber
import nltk

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

    def _extract_text_from_pdf(self, pdf_path: Path) -> Optional[str]:
        """
        Extract text content from a PDF file.
        
        Args:
            pdf_path (Path): Path to the PDF file
            
        Returns:
            Optional[str]: Extracted text if successful, None if file is scanned/unreadable
        """
        try:
            logging.info(f"Starting text extraction from {pdf_path}")
            
            with pdfplumber.open(pdf_path) as pdf:
                # List to store text from each page
                text_content = []
                
                # Process each page
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        text = page.extract_text()
                        if text:
                            text_content.append(text)
                        logging.info(f"Processed page {page_num}")
                    except Exception as e:
                        logging.error(f"Error processing page {page_num}: {str(e)}")
                        continue
                
                # Combine all text
                full_text = '\n'.join(text_content)
                
                # Check if we got meaningful text
                if len(full_text.strip()) < 10:  # Arbitrary minimum length
                    logging.warning("Extracted text is very short - might be a scanned PDF")
                    return None
                    
                return full_text
                
        except Exception as e:
            logging.error(f"Error extracting text from PDF: {str(e)}")
            return None

    def _create_chunks(self, text: str, max_chars: int = 7500) -> list[str]:
        chunks = []
        current_chunk = []
        current_length = 0

        # Split into sentences (simple split on periods)
        sentences = text.replace('\n', ' ').split('.')

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:  # Skip empty sentences
                continue

            sentence_with_period = sentence + '.'  # Add the period back
            sentence_length = len(sentence_with_period)

            if current_length + sentence_length > max_chars and current_chunk:
                # Current chunk is full, save it and start new chunk
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence_with_period]
                current_length = sentence_length
            else:
                # Add sentence to current chunk
                current_chunk.append(sentence_with_period)
                current_length += sentence_length

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks



    def process_paper(self, url: str):
        """
        Main method to process a paper from URL.
        
        Args:
            url (str): URL of the PDF to process
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
            
            # Extract text from PDF
            text_content = self._extract_text_from_pdf(pdf_path)
            if not text_content:
                raise RuntimeError("Failed to extract text - might be a scanned PDF")
            
            # Create chunks
            chunks = self._create_chunks(text_content)
            if not chunks:
                raise RuntimeError("Failed to create text chunks")
                
            logging.info(f"Successfully processed paper into {len(chunks)} chunks")
            
            # TODO: Next steps - OpenAI integration and summary generation
            
        except Exception as e:
            logging.error(f"Error processing paper from URL {url}: {str(e)}")
            raise

if __name__ == "__main__":
    # Create processor instance
    processor = PaperProcessor()
    
    # Test URL - "Attention Is All You Need" paper
    test_url = "https://arxiv.org/pdf/1706.03762.pdf"
    
    try:
        processor.process_paper(test_url)
        print("\nTest Summary:")
        print("✓ URL validation successful")
        print("✓ PDF download successful")
        print("✓ Text extraction successful")
        print("✓ Chunking successful")
        print("\nCheck the 'full_papers' directory for the downloaded PDF!")
        print("Check the 'error_log' directory for detailed logs!")
        
    except ValueError as e:
        print(f"URL Validation Error: {str(e)}")
    except RuntimeError as e:
        print(f"Processing Error: {str(e)}")
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")