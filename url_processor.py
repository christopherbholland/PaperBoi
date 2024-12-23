# url_processor.py

import re
import requests
from urllib.parse import urlparse
from typing import Tuple, Optional
import logging

class URLProcessor:
    """
    Handles URL processing and validation for academic papers.
    Specifically handles arXiv URLs and other academic paper repositories.
    """
    
    @staticmethod
    def normalize_arxiv_url(url: str) -> str:
        """
        Normalize arXiv URLs to PDF format.
        
        Args:
            url (str): Input URL like 'arxiv.org/abs/2305.10601'
            
        Returns:
            str: Normalized URL like 'arxiv.org/pdf/2305.10601.pdf'
        """
        # Extract arXiv ID using regex
        arxiv_patterns = [
            r'arxiv\.org/abs/(\d+\.\d+)',
            r'arxiv\.org/pdf/(\d+\.\d+)',
            r'arxiv\.org/\w+/(\d+\.\d+)'
        ]
        
        for pattern in arxiv_patterns:
            if match := re.search(pattern, url):
                arxiv_id = match.group(1)
                return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        
        return url

    @staticmethod
    def add_protocol(url: str) -> str:
        """
        Add https:// protocol if missing.
        
        Args:
            url (str): Input URL
            
        Returns:
            str: URL with protocol
        """
        if not url.startswith(('http://', 'https://')):
            return f'https://{url}'
        return url

    @staticmethod
    def get_final_pdf_url(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Process URL and return final PDF URL after following redirects.
        
        Args:
            url (str): Input URL
            
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: 
                (success, final_url, error_message)
        """
        try:
            # Add protocol if missing
            url = URLProcessor.add_protocol(url)
            
            # Check if URL is properly formatted
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                return False, None, "Invalid URL format"
            
            # Handle arXiv URLs specially
            if 'arxiv.org' in url.lower():
                url = URLProcessor.normalize_arxiv_url(url)
            
            # Try to access the URL
            try:
                response = requests.head(url, allow_redirects=True, timeout=10)
                response.raise_for_status()
                final_url = response.url
                
                # Check if content type is PDF
                content_type = response.headers.get('content-type', '').lower()
                if 'application/pdf' in content_type:
                    return True, final_url, None
                
                # If not PDF, try adding .pdf extension
                if not url.lower().endswith('.pdf'):
                    pdf_url = url + '.pdf'
                    try:
                        pdf_response = requests.head(pdf_url, allow_redirects=True, timeout=10)
                        pdf_response.raise_for_status()
                        if 'application/pdf' in pdf_response.headers.get('content-type', '').lower():
                            return True, pdf_url, None
                    except requests.RequestException:
                        pass
                
                return False, None, f"URL does not point to a PDF (content-type: {content_type})"
                
            except requests.RequestException as e:
                return False, None, f"Error accessing URL: {str(e)}"
            
        except Exception as e:
            return False, None, f"Error processing URL: {str(e)}"

def get_paper_url_from_user() -> Optional[str]:
    """
    Get paper URL from user input with validation.
    Handles different URL formats and provides feedback.
    
    Returns:
        Optional[str]: Valid paper URL or None if user cancels
    """
    while True:
        print("\nEnter the URL of the academic paper (or 'q' to quit):")
        url = input().strip()
        
        if url.lower() == 'q':
            return None
            
        success, final_url, error = URLProcessor.get_final_pdf_url(url)
        
        if success:
            print(f"Valid PDF URL found: {final_url}")
            return final_url
        else:
            print(f"Error: {error}")
            print("Please try again with a valid URL")

if __name__ == "__main__":
    # Test the URL processor
    test_urls = [
        "https://arxiv.org/abs/2305.10601",
        "arxiv.org/pdf/2305.10601",
        "https://arxiv.org/pdf/2305.10601.pdf",
        "invalid-url",
    ]
    
    print("Testing URL processor...")
    for url in test_urls:
        print(f"\nTesting URL: {url}")
        success, final_url, error = URLProcessor.get_final_pdf_url(url)
        if success:
            print(f"Success! Final URL: {final_url}")
        else:
            print(f"Error: {error}")