###################
# Standard Imports
###################
# Python's built-in libraries - these come with Python installation
import os                  # Operating system interface (file paths, env vars)
from pathlib import Path   # Object-oriented way to handle file paths
from datetime import datetime  # For working with dates and times
import logging            # For logging errors and info messages
import re                 # Regular expressions for pattern matching
from typing import Optional, Tuple  # Type hints for better code clarity
from urllib.parse import urlparse   # Tools for URL parsing

###################
# External Imports
###################
# Third-party libraries - need to be installed via pip
from dotenv import load_dotenv  # Loads environment variables from .env file
import requests               # HTTP library for making web requests
import pdfplumber            # PDF text extraction library
from tqdm import tqdm        # Progress bar library

###################
# Local Imports
###################
# Our own modules from this project
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
    
    Python Class Concepts:
    - Classes are like blueprints for creating objects
    - Methods (functions in a class) automatically get 'self' as first parameter
    - 'self' refers to the instance of the class being created
    """

    ###################
    # Initialization
    ###################
    def __init__(self):
        """
        Constructor method - runs when creating a new PaperProcessor object
        
        Python Concepts:
        - __init__ is a special method (note the double underscores)
        - It's called automatically when creating a new instance
        - Used to set up initial state of the object
        """
        # Load environment variables from .env file
        load_dotenv()
        
        # Initialize configuration
        # The following lines show object composition - creating objects inside other objects
        self.config = ProcessorConfig()
        self.config.create_directories()
        
        self.metadata_manager = MetadataManager(self.config.metadata_dir)
        
        self._setup_logging()
        
        # Example of try/except for error handling
        try:
            self.openai = OpenAIIntegration(assistant_id="asst_wZ5zEV6sMvWehfujffAd6pO2")
            logging.info("Successfully initialized OpenAI integration")
        except Exception as e:
            # Using f-strings (note the f before the string) for string formatting
            logging.error(f"Failed to initialize OpenAI integration: {str(e)}")
            raise  # Re-raise the exception after logging it

    ###################
    # Logging Setup
    ###################
    def _setup_logging(self):
        """
        Configure logging to both file and console.
        
        Python Concepts:
        - Methods starting with underscore (_) are conventionally "private"
        - They're meant to be used only inside the class, not from outside
        """
        # Using Path objects for file paths (better than string concatenation)
        log_file = self.config.errors_dir / f'error_log_{datetime.now().strftime("%Y%m%d")}.log'
        
        # Dictionary unpacking using ** operator
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()  # Prints to console
            ]
        )

    ###################
    # Text Processing
    ###################
    def create_chunks(self, text: str, max_chars: int = 7500) -> list[str]:
        """
        Split text into chunks at sentence boundaries.
        
        Python Concepts:
        - Type hints (str, int, list[str]) make code more readable
        - Default parameter values (max_chars=7500)
        - List comprehension and string manipulation
        
        Args:
            text (str): The text to split into chunks
            max_chars (int, optional): Maximum characters per chunk. Defaults to 7500.
            
        Returns:
            list[str]: List of text chunks
        """
        # Regular expression split - matches periods, exclamation marks, question marks
        # followed by whitespace
        sentences = re.split(r'(?<=[.!?])\s+', text.replace('\n', ' '))
        
        # List to store our chunks
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Demonstrating iteration and list building
        for sentence in sentences:
            if not sentence.strip():  # Skip empty sentences
                continue
                
            # If adding this sentence would make chunk too long,
            # save current chunk and start a new one
            if current_length + len(sentence) > max_chars and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0
                
            current_chunk.append(sentence)
            current_length += len(sentence)
        
        # Don't forget the last chunk!
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    ###################
    # URL Processing
    ###################
    def _validate_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if the URL points to a PDF.
        
        Python Concepts:
        - Type hints with Optional (means it can be None)
        - Tuple return types (returning multiple values)
        - Using external class methods
        
        Args:
            url (str): URL to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        success, final_url, error = URLProcessor.get_final_pdf_url(url)
        return success, error

    ###################
    # File Operations
    ###################
    def _download_pdf(self, url: str) -> Optional[Path]:
        """
        Download PDF from URL and save to papers directory.
        
        Python Concepts:
        - Context managers (with statement)
        - File handling
        - Error handling with try/except
        """
        try:
            # Create unique filename using timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"paper_{timestamp}.pdf"
            file_path = self.config.papers_dir / filename
            
            # Download file in chunks to handle large files
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raises exception for bad HTTP status
            
            # Context manager ensures file is properly closed after writing
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
            
            Python Concepts:
            - Context managers (with statement) for PDF handling
            - List comprehension for collecting text
            - String join operations
            - Length checking with str.strip()
            
            Args:
                pdf_path (Path): Path to the PDF file
                
            Returns:
                Optional[str]: Extracted text or None if extraction fails
            """
    def _extract_text_from_pdf(self, pdf_path: Path) -> Optional[str]:
        """
        Extract text content from a PDF file.
        
        Python Concepts:
        - Context managers (with statement) for PDF handling
        - List comprehension for collecting text
        - String join operations
        - Length checking with str.strip()
        
        Args:
            pdf_path (Path): Path to the PDF file
            
        Returns:
            Optional[str]: Extracted text or None if extraction fails
        """
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
        """
        Extract and sanitize paper title from summary.
        
        Python Concepts:
        - Regular expressions (re module)
        - String manipulation and cleaning
        - Method chaining with string methods
        - Error handling with try/except
        
        Args:
            summary (str): Summary text containing title in [[title]] format
            
        Returns:
            str: Sanitized title or "untitled_paper" if extraction fails
        """
        try:
            # Extract text between [[ and ]] using regex
            # re.search returns a match object or None
            match = re.search(r'\[\[(.*?)\]\]', summary)
            if not match:
                logging.warning("Could not find paper title in [[ ]] format")
                return "untitled_paper"
                
            # Extract the actual title text from the match
            # group(1) gets the content inside the parentheses in the regex
            title = match.group(1).strip()
            
            # Chain of replacements to clean the title:
            # 1. Replace invalid filename characters with underscores
            title = re.sub(r'[<>:"/\\|?*]', '_', title)
            # 2. Replace multiple spaces or underscores with single underscore
            title = re.sub(r'[\s_]+', '_', title)
            # 3. Remove leading/trailing underscores
            title = title.strip('_')
            
            return title
            
        except Exception as e:
            logging.error(f"Error extracting title from summary: {str(e)}")
            return "untitled_paper"

    ###################
    # Main Processing
    ###################
    def process_paper(self, url: str) -> Optional[PaperMetadata]:
        """
        Main method to process a paper from URL.
        
        Python Concepts:
        - Complex error handling with multiple steps
        - Using type hints for complex return types
        - Logging for process tracking
        - Working with optional returns
        
        Args:
            url (str): URL of the paper to process
            
        Returns:
            Optional[PaperMetadata]: Metadata of processed paper or None if processing fails
        """
        try:
            # Log the start of processing
            logging.info(f"Starting to process paper from URL: {url}")
            
            # Validate and download - note the use of multiple steps with error checking
            is_valid, error_message = self._validate_url(url)
            if not is_valid:
                raise ValueError(f"Invalid URL: {error_message}")
            
            pdf_path = self._download_pdf(url)
            if not pdf_path:  # None check for optional return
                raise RuntimeError("Failed to download PDF")
            
            # Extract and process text
            text_content = self._extract_text_from_pdf(pdf_path)
            if not text_content:
                raise RuntimeError("Failed to extract text - might be a scanned PDF")
            
            # Create chunks of text
            chunks = self.create_chunks(text_content)
            if not chunks:
                raise RuntimeError("Failed to create text chunks")
            
            # Process with OpenAI - note the step-by-step error checking
            if not self.openai.start_new_chat(len(chunks)):
                raise RuntimeError("Failed to start OpenAI thread")
            
            # Enumerate gives us both index and value in a loop
            for i, chunk in enumerate(chunks, 1):  # Start counting at 1
                if not self.openai.send_chunk(chunk, i, len(chunks)):
                    raise RuntimeError(f"Failed to process chunk {i}")
            
            # Get and validate summary
            summary = self.openai.request_summary()
            if not summary:
                raise RuntimeError("Failed to generate summary")
            
            # Create filename from title and timestamp
            paper_title = self._extract_and_sanitize_title(summary)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_filename = f"{paper_title}_{timestamp}.txt"
            summary_path = self.config.summaries_dir / summary_filename
            
            # Save summary
            if not self.openai.save_summary(summary, summary_path):
                raise RuntimeError("Failed to save summary")
            
            # Create metadata object - note how we create a complex object
            metadata = PaperMetadata(
                original_filename=pdf_path.name,
                original_url=url,
                num_chunks=len(chunks),
                title=paper_title,
                doi=None,  # Could add DOI extraction if needed
                summary_path=str(summary_path)
            )
            
            # Save metadata and return
            self.metadata_manager.save_paper_metadata(metadata)
            return metadata
            
        except Exception as e:
            # Log error and re-raise to let caller handle it
            logging.error(f"Error processing paper from URL {url}: {str(e)}")
            raise

    ###################
    # Utility Methods
    ###################
    def list_processed_papers(self) -> list[dict]:
        """
        Return list of all processed papers, sorted by date.
        
        Python Concepts:
        - Working with dictionaries and lists
        - Sorting with key functions
        - List comprehension
        - Dictionary methods
        
        Returns:
            list[dict]: List of paper metadata dictionaries
        """
        # Load master data (dictionary of papers)
        master_data = self.metadata_manager.load_master()
        
        # Convert dictionary values to list
        papers = list(master_data.values())
        
        # Sort papers by date (newest first)
        # The lambda function creates a sorting key based on processing_date
        papers.sort(key=lambda x: x['processing_date'], reverse=True)
        
        return papers


###################
# Main Execution
###################
if __name__ == "__main__":
    """
    Python Concepts:
    - __name__ == "__main__" idiom for script entry point
    - Basic error handling
    - User interaction
    - String formatting
    """
    # Create processor instance
    processor = PaperProcessor()
    
    try:
        # Get URL from user - note the clear error handling structure
        url = get_paper_url_from_user()
        if url:
            # Process the paper
            metadata = processor.process_paper(url)
            # f-strings for clean string formatting
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

"""
Key Python Concepts Used in This Code:

1. Object-Oriented Programming (OOP):
   - Class definition and inheritance
   - Instance methods vs class methods
   - Encapsulation (private methods with _)
   - Object composition

2. Type Hints:
   - Optional[Type] for nullable values
   - Tuple[Type1, Type2] for multiple return values
   - list[Type] for list contents
   - -> for return type hints

3. Error Handling:
   - try/except blocks
   - Exception hierarchy
   - Logging errors
   - Re-raising exceptions

4. File Operations:
   - Context managers (with statements)
   - Path handling with pathlib
   - File reading and writing
   - Binary vs text mode

5. Modern Python Features:
   - f-strings for string formatting
   - Type hints for better code clarity
   - Pathlib for file operations
   - Optional types from typing module

6. Common Patterns:
   - Configuration management
   - Logging setup
   - URL handling
   - File downloading
   - Text processing
"""