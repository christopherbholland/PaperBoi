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
from url_processor import URLProcessor, get_paper_url_from_user  # New import
from openai_integration import OpenAIIntegration

class PaperProcessor:
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

    def _setup_logging(self):
        log_file = self.config.errors_dir / f'error_log_{datetime.now().strftime("%Y%m%d")}.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

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

    def _validate_url(self, url: str) -> Tuple[bool, Optional[str]]:
        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                return False, "Invalid URL format"
            
            response = requests.head(url, allow_redirects=True)
            
            content_type = response.headers.get('content-type', '').lower()
            if 'application/pdf' not in content_type:
                return False, f"URL does not point to a PDF (content-type: {content_type})"
            
            return True, None
            
        except requests.RequestException as e:
            return False, f"Error validating URL: {str(e)}"

    def _download_pdf(self, url: str) -> Optional[Path]:
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

    def _extract_and_sanitize_title(self, summary: str) -> str:
        """
        Extract the paper title from [[ ]] in summary and sanitize it for use as filename.
        """
        try:
            # Extract text between [[ and ]]
            match = re.search(r'\[\[(.*?)\]\]', summary)
            if not match:
                logging.warning("Could not find paper title in [[ ]] format")
                return "untitled_paper"
                
            title = match.group(1).strip()
            
            # Sanitize for filename
            # Replace invalid filename characters with underscores
            title = re.sub(r'[<>:"/\\|?*]', '_', title)
            # Replace multiple spaces/underscores with single underscore
            title = re.sub(r'[\s_]+', '_', title)
            # Remove any leading/trailing underscores
            title = title.strip('_')
            
            return title
            
        except Exception as e:
            logging.error(f"Error extracting title from summary: {str(e)}")
            return "untitled_paper"

    def process_paper(self, url: str) -> Optional[PaperMetadata]:
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
                doi=None,  # Could add DOI extraction if needed
                summary_path=str(summary_path)
            )
            
            self.metadata_manager.save_paper_metadata(metadata)
            return metadata
            
        except Exception as e:
            logging.error(f"Error processing paper from URL {url}: {str(e)}")
            raise

    def list_processed_papers(self) -> list[dict]:
        master_data = self.metadata_manager.load_master()
        papers = list(master_data.values())
        papers.sort(key=lambda x: x['processing_date'], reverse=True)
        return papers

    def _validate_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if the URL points to a PDF.
        
        Args:
            url (str): URL to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        success, final_url, error = URLProcessor.get_final_pdf_url(url)
        return success, error

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