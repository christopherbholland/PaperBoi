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
import json
from openai_integration import OpenAIIntegration
from openai import OpenAI
from tqdm import tqdm

class PaperProcessor:
    """
    A class to process academic papers from URLs, extract text, and manage metadata.
    """
    
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

        # Inside PaperProcessor.__init__
        try:
            self.openai = OpenAIIntegration(assistant_id="asst_wZ5zEV6sMvWehfujffAd6pO2")
            logging.info("Successfully initialized OpenAI integration")
        except Exception as e:
            logging.error(f"Failed to initialize OpenAI integration: {str(e)}")
            raise
        
    def _create_directories(self):
        """
        Create necessary directories if they don't exist.
        Creates directories for papers, summaries, metadata, and error logs.
        Also initializes the master papers JSON file if it doesn't exist.
        """
        # Create directories
        for dir_path in self.directories.values():
            dir_path.mkdir(exist_ok=True)
            
        # Initialize master papers file if it doesn't exist
        self.master_file = self.directories['metadata'] / 'all_papers.json'
        if not self.master_file.exists():
            self._save_to_master_file({})
            
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

    def _extract_first_pages(self, pdf_path: Path, max_pages: int = 3) -> Optional[str]:
        """
        Extract text from first few pages of PDF where title and DOI are likely to be.
        
        Args:
            pdf_path (Path): Path to PDF file
            max_pages (int): Maximum number of pages to extract
            
        Returns:
            Optional[str]: Extracted text from first pages
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                pages_to_check = min(len(pdf.pages), max_pages)
                text_content = []
                
                for page_num in range(pages_to_check):
                    text = pdf.pages[page_num].extract_text()
                    if text:
                        text_content.append(text)
                        
                return '\n'.join(text_content)
                
        except Exception as e:
            logging.error(f"Error extracting first pages: {str(e)}")
            return None

    def _extract_title(self, text: str) -> Optional[str]:
        """
        Extract paper title using various heuristics.
        
        Args:
            text (str): Text content to search for title
            
        Returns:
            Optional[str]: Extracted title or None if not found
        """
        # Common patterns that often precede or follow titles
        patterns = [
            # Look for text between abstract and introduction
            r"(?:abstract\s*\n+)(.*?)(?:\n+\s*(?:introduction|keywords))",
            # Look for first line after arxiv identifier
            r"(?:arXiv:\d+\.\d+v?\d*\s*\n+)(.*?)(?:\n)",
            # Look for first line(s) of document
            r"^\s*((?:[^\n]+\n){1,3})"
        ]
        
        for pattern in patterns:
            matches = re.search(pattern, text.lower())
            if matches:
                # Get the first matching group and clean it up
                title = matches.group(1)
                # Clean up the extracted title
                title = re.sub(r'\s+', ' ', title)  # Replace multiple spaces/newlines
                title = title.strip()
                if len(title) > 10:  # Arbitrary minimum length to avoid garbage
                    return title.title()  # Convert to title case
                    
        return None

    def _extract_doi(self, text: str) -> Optional[str]:
        """
        Extract DOI using regex patterns.
        
        Args:
            text (str): Text content to search for DOI
            
        Returns:
            Optional[str]: Extracted DOI or None if not found
        """
        # DOI patterns
        doi_patterns = [
            # Standard DOI format
            r"(?:doi:|DOI:|https://doi.org/)(10\.\d{4,}/[-._;()/:\w]+)",
            # DOI without prefix
            r"\b(10\.\d{4,}/[-._;()/:\w]+)\b"
        ]
        
        for pattern in doi_patterns:
            match = re.search(pattern, text)
            if match:
                doi = match.group(1)
                # Clean up the DOI
                doi = doi.strip().rstrip('.')
                return doi
                
        return None

    def _extract_metadata_from_pdf(self, pdf_path: Path, text_content: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract title and DOI from PDF file or existing text content.
        
        Args:
            pdf_path (Path): Path to the PDF file
            text_content (Optional[str]): Pre-extracted text content, if available
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (title, doi)
        """
        try:
            # If text content wasn't provided, get it from first few pages
            if not text_content:
                text_content = self._extract_first_pages(pdf_path)
                if not text_content:
                    return None, None
                    
            # Extract title and DOI
            title = self._extract_title(text_content)
            doi = self._extract_doi(text_content)
            
            return title, doi
            
        except Exception as e:
            logging.error(f"Error extracting title and DOI: {str(e)}")
            return None, None

    def _create_chunks(self, text: str, max_chars: int = 7500) -> list[str]:
        """
        Split text into chunks while preserving sentence boundaries.
        
        Args:
            text (str): Text to split into chunks
            max_chars (int): Maximum characters per chunk
            
        Returns:
            list[str]: List of text chunks
        """
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

    def _load_master_file(self) -> dict:
        """
        Load the master papers JSON file.
        
        Returns:
            dict: Dictionary containing all paper metadata
        """
        try:
            with open(self.master_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            logging.error("Master file corrupted, creating new one")
            return {}

    def _save_to_master_file(self, data: dict):
        """
        Save data to the master papers JSON file.
        
        Args:
            data (dict): Data to save
        """
        with open(self.master_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def _save_metadata(self, metadata: dict) -> Path:
        """
        Save metadata to individual JSON file and update master file.
        
        Args:
            metadata (dict): Metadata dictionary to save
            
        Returns:
            Path: Path to saved metadata file
        """
        try:
            # Create filename based on processing date
            filename = f"metadata_{metadata['processing_date'].replace(':', '-')}.json"
            file_path = self.directories['metadata'] / filename
            
            # Save individual metadata file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=4)
                
            # Update master file
            master_data = self._load_master_file()
            
            # Use DOI as key if available, otherwise use filename
            paper_key = metadata.get('doi') or metadata['original_filename']
            master_data[paper_key] = metadata
            
            # Save updated master file
            self._save_to_master_file(master_data)
                
            logging.info(f"Saved metadata to {file_path} and updated master file")
            return file_path
            
        except Exception as e:
            logging.error(f"Error saving metadata: {str(e)}")
            raise

    def _create_metadata(self, url: str, pdf_path: Path, num_chunks: int, 
                        title: Optional[str] = None, doi: Optional[str] = None) -> dict:
        """
        Create metadata dictionary for paper processing.
        
        Args:
            url (str): Original URL of the PDF
            pdf_path (Path): Path to the downloaded PDF
            num_chunks (int): Number of text chunks created
            title (Optional[str]): Extracted paper title
            doi (Optional[str]): Extracted DOI
            
        Returns:
            dict: Metadata dictionary with processing information
        """
        timestamp = datetime.now()
        
        metadata = {
            "original_filename": pdf_path.name,
            "summary_filename": f"summary_{pdf_path.stem}.txt",
            "processing_date": timestamp.isoformat(),
            "original_url": url,
            "num_chunks": num_chunks,
            "title": title,
            "doi": doi
        }
        
        return metadata
    

    def list_processed_papers(self) -> list[dict]:
        """
        Get a list of all processed papers with their metadata.
        
        Returns:
            list[dict]: List of paper metadata dictionaries
        """
        master_data = self._load_master_file()
        
        # Convert to list and sort by processing date
        papers = list(master_data.values())
        papers.sort(key=lambda x: x['processing_date'], reverse=True)
        
        return papers

    def process_paper(self, url: str) -> Optional[dict]:
        """
        Main method to process a paper from URL.
        Downloads PDF, extracts text, processes with OpenAI Assistant, and saves results.
        
        Args:
            url (str): URL of the PDF to process
            
        Returns:
            Optional[dict]: Processing metadata if successful, None if failed
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
            
            # Extract title and DOI
            title, doi = self._extract_metadata_from_pdf(pdf_path, text_content)
            logging.info(f"Extracted title: {title}")
            logging.info(f"Extracted DOI: {doi}")
            
            # Create chunks
            chunks = self._create_chunks(text_content)
            if not chunks:
                raise RuntimeError("Failed to create text chunks")
                
            # Start OpenAI Assistant thread
            if not self.openai.start_new_chat(len(chunks)):
                raise RuntimeError("Failed to start OpenAI thread")
                
            # Process chunks with progress bar
            logging.info(f"Processing {len(chunks)} chunks with OpenAI")
            for i, chunk in enumerate(tqdm(chunks, desc="Processing chunks"), 1):
                if not self.openai.send_chunk(chunk, i, len(chunks)):
                    raise RuntimeError(f"Failed to process chunk {i}")
                    
            # Generate summary using Assistant
            summary = self.openai.request_summary()
            if not summary:
                raise RuntimeError("Failed to generate summary")
                
            # Save summary to file
            summary_filename = f"summary_{pdf_path.stem}.txt"
            summary_path = self.directories['summaries'] / summary_filename
            if not self.openai.save_summary(summary, summary_path):
                raise RuntimeError("Failed to save summary")
            
            # Create and save metadata
            metadata = self._create_metadata(url, pdf_path, len(chunks), title, doi)
            metadata['summary_path'] = str(summary_path)
            metadata_path = self._save_metadata(metadata)
            
            logging.info("Successfully completed paper processing")
            return metadata
            
        except Exception as e:
            logging.error(f"Error processing paper from URL {url}: {str(e)}")
            raise

if __name__ == "__main__":
        # Create processor instance
        processor = PaperProcessor()
        
        # Test URL - "Attention Is All You Need" paper
        test_url = "https://arxiv.org/pdf/1706.03762.pdf"
        
        try:
            metadata = processor.process_paper(test_url)
            print("\nTest Summary:")
            print("✓ URL validation successful")
            print("✓ PDF download successful")
            print("✓ Text extraction successful")
            print("✓ Title and DOI extraction attempted")
            print("✓ Chunking successful")
            print("✓ Metadata saved")
            
            print("\nMetadata created:")
            for key, value in metadata.items():
                print(f"  {key}: {value}")
                
            print("\nAll processed papers:")
            papers = processor.list_processed_papers()
            for i, paper in enumerate(papers, 1):
                title = paper.get('title') or "Unknown Title"
                date = paper.get('processing_date', '').split('T')[0]  # Just the date part
                print(f"{i}. {title} (processed: {date})")
                
            print("\nCheck the following files/directories:")
            print("- 'full_papers' for the downloaded PDFs")
            print("- 'metadata/all_papers.json' for the complete paper database")
            print("- 'metadata' for individual JSON metadata files")
            print("- 'error_log' for detailed logs")
                
        except ValueError as e:
            print(f"URL Validation Error: {str(e)}")
        except RuntimeError as e:
            print(f"Processing Error: {str(e)}")
        except Exception as e:
            print(f"Unexpected Error: {str(e)}")