requirements doc

22 Deceember 19:24

✓ Done:
1. System Structure (directories created)
2. Input and Validation (URL handling)
3. PDF Processing (extraction & chunking)
4. Metadata Management (JSON storage + master file)
5. File Management (file naming and storage)
6. Error Handling (logging)
7. Configuration (environment loading)

Still needed:
1. **OpenAI Integration**:
   * Load API key from .env file
   * Start new chat with PaperBoi assistant
   * Send total chunk count information
   * Upload chunks sequentially
   * Handle basic upload errors

2. **Summary Generation**:
   * Request summary from PaperBoi
   * Ensure summary includes paper name in `[[Name of paper]]` format




===


# Paper Processing System Requirements
## Overview
This system automates the process of downloading academic papers, processing them for AI analysis, and storing their summaries. It accepts PDF URLs as input, processes the papers into chunks suitable for OpenAI's context window, uses a specialized PaperBoi assistant to generate summaries, and maintains an organized file structure with the original papers, summaries, and metadata. The system is designed for single-user use and prioritizes reliability and simplicity over advanced features.
## Requirements
1. **System Structure**:
   * Create and maintain four main directories:
     - Full Papers
     - PaperBoi Summaries
     - Metadata
     - Error Log
2. **Input and Validation**:
   * Accept a URL as input
   * Handle URL redirects
   * Validate that the final URL points to a PDF
   * Download and store the PDF
3. **PDF Processing**:
   * Extract text content from text-based PDFs
   * Skip OCR for scanned PDFs (handle manually)
   * Break content into ~7500 character chunks
   * Avoid splitting mid-sentence where possible
4. **Metadata Management**:
   * Store paper metadata in JSON format including:
     - Original filename
     - Summary filename
     - Processing date
     - Original URL
     - Title (if extractable)
     - DOI (if available)
     - Number of chunks processed
   * Check JSON before processing to avoid duplicates
5. **OpenAI Integration**:
   * Load API key from .env file
   * Start new chat with PaperBoi assistant
   * Send total chunk count information
   * Upload chunks sequentially
   * Handle basic upload errors
6. **Summary Generation**:
   * Request summary from PaperBoi
   * Ensure summary includes paper name in `[[Name of paper]]` format
7. **File Management**:
   * Remove symbols from filenames
   * Generate unique filenames using timestamps
   * Store files in appropriate directories
   * Keep original PDFs
8. **Error Handling**:
   * Log all errors with timestamps
   * Include relevant debugging information
   * Continue processing on non-critical errors
9. **Configuration**:
   * Store API key in .env file
   * Include .env in .gitignore
   * Single user system, no authentication needed