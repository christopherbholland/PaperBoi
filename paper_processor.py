###################
# Standard Imports
###################
import os
from pathlib import Path
from datetime import datetime
import logging
import re
from typing import Optional, Tuple
from urllib.parse import urlparse

###################
# External Imports
###################
from dotenv import load_dotenv
import requests
import pdfplumber
from tqdm import tqdm

###################
# Local Imports
###################
from config import ProcessorConfig, PaperMetadata, MetadataManager
from url_processor import URLProcessor, get_paper_url_from_user
from openai_integration import OpenAIIntegration

###################
# Main Class
###################
class PaperProcessor:
    """
    Main class for processing academic papers from URLs.
    Downloads, processes, and generates summaries using OpenAI.
    """

    ###################
    # Initialization
    ###################
    def __init__(self):
        load_dotenv()
        
        # Initialize configuration
        self.config = ProcessorConfig()
        self.config.create_directories()
        
        # Initialize metadata manager
        self.metadata_manager = MetadataManager(self.config.metadata_dir)
        
        # Set up logging
        self._setup_logging()
        
        # Initialize OpenAI integration
        try:
            self.openai = OpenAIIntegration(assistant_id="asst_wZ5zEV6sMvWehfujffAd6pO2")
            logging.info("Successfully initialized OpenAI integration")
        except Exception as e:
            logging.error(f"Failed to initialize OpenAI integration: {str(e)}")
            raise

    ###################
    # Logging Setup
    ###################
    def _setup_logging(self):
        """Configure logging to both file and console."""
        log_file = self.config.errors_dir / f'error_log_{datetime.now().strftime("%Y%m%d")}.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

    ###################
    # Text Processing
    ###################
    def create_chunks(self, text: str, max_chars: int = 7500) -> list[str]:
        """Split text into chunks at sentence boundaries."""
        sentences = re.split(r'(?<=[.!?])\s+', text.replace('\n', ' '))
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            if current_length + len(sentence) > max_chars and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0
                
            current_chunk.append(sentence)
            current_length += len(sentence)
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    ###################
    # URL Processing
    ###################
    def _validate_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """Validate if the URL points to a PDF."""
        success, final_url, error = URLProcessor.get_final_pdf_url(url)
        return success, error

    ###################
    # File Operations
    ###################
    def _download_pdf(self, url: str) -> Optional[Path]:
        """Download PDF from URL and save to papers directory."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"paper_{timestamp}.pdf"
            file_path = self.config.papers_dir / filename
            
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
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
        """Extract text content from a PDF file."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text_content = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
                
                full_text = '\n'.join(text_content)
                if len(full_text.strip()) < 10:
                    return None
                    
                return full_text
                
        except Exception as e:
            logging.error(f"Error extracting text from PDF: {str(e)}")
            return None

    ###################
    # Title Processing
    ###################
    def _extract_and_sanitize_title(self, summary: str) -> str:
        """Extract and sanitize paper title from summary."""
        try:
            match = re.search(r'\[\[(.*?)\]\]', summary)
            if not match:
                logging.warning("Could not find paper title in [[ ]] format")
                return "untitled_paper"
                
            title = match.group(1).strip()
            title = re.sub(r'[<>:"/\\|?*]', '_', title)
            title = re.sub(r'[\s_]+', '_', title)
            title = title.strip('_')
            
            return title
            
        except Exception as e:
            logging.error(f"Error extracting title from summary: {str(e)}")
            return "untitled_paper"

    ###################
    # Main Processing
    ###################
    def process_paper(self, url: str) -> Optional[PaperMetadata]:
        """Main method to process a paper from URL."""
        try:
            logging.info(f"Starting to process paper from URL: {url}")
            
            # Validate and download
            is_valid, error_message = self._validate_url(url)
            if not is_valid:
                raise ValueError(f"Invalid URL: {error_message}")
            
            pdf_path = self._download_pdf(url)
            if not pdf_path:
                raise RuntimeError("Failed to download PDF")
            
            # Extract and process text
            text_content = self._extract_text_from_pdf(pdf_path)
            if not text_content:
                raise RuntimeError("Failed to extract text - might be a scanned PDF")
            
            # Create chunks
            chunks = self.create_chunks(text_content)
            if not chunks:
                raise RuntimeError("Failed to create text chunks")
            
            # Process with OpenAI
            if not self.openai.start_new_chat(len(chunks)):
                raise RuntimeError("Failed to start OpenAI thread")
            
            for i, chunk in enumerate(chunks, 1):
                if not self.openai.send_chunk(chunk, i, len(chunks)):
                    raise RuntimeError(f"Failed to process chunk {i}")
            
            # Get summary
            summary = self.openai.request_summary()
            if not summary:
                raise RuntimeError("Failed to generate summary")
            
            # Extract title and create filename
            paper_title = self._extract_and_sanitize_title(summary)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_filename = f"{paper_title}_{timestamp}.txt"
            summary_path = self.config.summaries_dir / summary_filename
            
            if not self.openai.save_summary(summary, summary_path):
                raise RuntimeError("Failed to save summary")
            
            # Create and save metadata
            metadata = PaperMetadata(
                original_filename=pdf_path.name,
                original_url=url,
                num_chunks=len(chunks),
                title=paper_title,
                doi=None,
                summary_path=str(summary_path)
            )
            
            self.metadata_manager.save_paper_metadata(metadata)
            return metadata
            
        except Exception as e:
            logging.error(f"Error processing paper from URL {url}: {str(e)}")
            raise

    ###################
    # Utility Methods
    ###################
    def list_processed_papers(self) -> list[dict]:
        """Return list of all processed papers, sorted by date."""
        master_data = self.metadata_manager.load_master()
        papers = list(master_data.values())
        papers.sort(key=lambda x: x['processing_date'], reverse=True)
        return papers

###################
# Main Execution
###################
if __name__ == "__main__":
    processor = PaperProcessor()
    
    try:
        # Get URL from user
        url = get_paper_url_from_user()
        if url:
            # Process the paper
            metadata = processor.process_paper(url)
            print(f"\nProcessed paper: {metadata.title}")
            print(f"Summary saved to: {metadata.summary_path}")
        else:
            print("\nOperation cancelled by user.")
            
    except Exception as e:
        print(f"Error: {str(e)}")

###################
# Function Overview
###################
"""
Class: PaperProcessor

Initialization Methods:
- __init__(): Initialize the processor with necessary configurations
- _setup_logging(): Configure logging settings

Text Processing Methods:
- create_chunks(text, max_chars): Split text into manageable chunks

URL Processing Methods:
- _validate_url(url): Validate if URL points to a PDF

File Operations:
- _download_pdf(url): Download PDF from given URL
- _extract_text_from_pdf(pdf_path): Extract text content from PDF

Title Processing:
- _extract_and_sanitize_title(summary): Extract and clean paper title

Main Processing:
- process_paper(url): Main method to process paper from URL

Utility Methods:
- list_processed_papers(): List all processed papers

Each method includes error handling and logging for reliability.
See method docstrings for detailed information.
"""