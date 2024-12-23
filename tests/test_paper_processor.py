# test_paper_processor.py

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from paper_processor import PaperProcessor, PaperMetadata

@pytest.fixture
def processor():
    """
    Fixture to create a PaperProcessor instance with ProcessorConfig, MetadataManager,
    OpenAIIntegration, and logging.FileHandler mocked.
    """
    with patch('paper_processor.ProcessorConfig') as mock_processor_config, \
         patch('paper_processor.MetadataManager') as mock_metadata_manager, \
         patch('paper_processor.OpenAIIntegration') as mock_openai_integration, \
         patch('paper_processor.logging.FileHandler') as mock_file_handler:
        
        # Mock ProcessorConfig
        mock_config_instance = MagicMock()
        mock_config_instance.metadata_dir = Path('/fake/metadata')
        mock_config_instance.papers_dir = Path('/fake/path')
        mock_config_instance.summaries_dir = Path('/fake/summaries')
        mock_config_instance.errors_dir = Path('/fake/errors')
        mock_config_instance.create_directories = MagicMock()
        mock_processor_config.return_value = mock_config_instance

        # Mock MetadataManager
        mock_metadata_manager_instance = MagicMock()
        # Define the return value for load_master to prevent FileNotFoundError
        mock_metadata_manager_instance.load_master.return_value = {}
        mock_metadata_manager.return_value = mock_metadata_manager_instance

        # Mock OpenAIIntegration
        mock_openai_instance = MagicMock()
        mock_openai_instance.start_new_chat.return_value = True
        mock_openai_instance.send_chunk.return_value = True
        mock_openai_instance.request_summary.return_value = "This is a summary with the title [[Sample Paper Title]]. More text."
        mock_openai_instance.save_summary.return_value = True
        mock_openai_integration.return_value = mock_openai_instance

        # Mock logging.FileHandler to prevent actual file I/O
        mock_file_handler_instance = MagicMock()
        mock_file_handler.return_value = mock_file_handler_instance

        # Instantiate PaperProcessor with all dependencies mocked
        processor_instance = PaperProcessor()

        yield processor_instance

        # No cleanup necessary as mocks are context-managed

def test_create_chunks_basic(processor):
    text = "This is sentence one. This is sentence two! Is this sentence three? Yes, it is."
    chunks = processor.create_chunks(text, max_chars=50)
    assert len(chunks) == 2
    assert chunks[0] == "This is sentence one. This is sentence two!"
    assert chunks[1] == "Is this sentence three? Yes, it is."

def test_create_chunks_exact_limit(processor):
    text = "A" * 7500
    chunks = processor.create_chunks(text, max_chars=7500)
    assert len(chunks) == 1
    assert chunks[0] == text

def test_create_chunks_empty_string(processor):
    text = ""
    chunks = processor.create_chunks(text)
    assert chunks == []

def test_extract_and_sanitize_title_success(processor):
    summary = "This is a summary with the title [[Sample Paper Title]]. More text."
    sanitized_title = processor._extract_and_sanitize_title(summary)
    assert sanitized_title == "Sample_Paper_Title"

def test_extract_and_sanitize_title_no_title(processor):
    summary = "This summary does not contain a title."
    sanitized_title = processor._extract_and_sanitize_title(summary)
    assert sanitized_title == "untitled_paper"

def test_extract_and_sanitize_title_invalid_chars(processor):
    summary = "Summary with title [[Invalid/Title:Name?]]."
    sanitized_title = processor._extract_and_sanitize_title(summary)
    assert sanitized_title == "Invalid_Title_Name"

@patch('paper_processor.URLProcessor.get_final_pdf_url')
def test_validate_url_success(mock_get_final_pdf_url, processor):
    mock_get_final_pdf_url.return_value = (True, "http://example.com/paper.pdf", None)
    is_valid, error = processor._validate_url("http://example.com/paper.pdf")
    assert is_valid is True
    assert error is None

@patch('paper_processor.URLProcessor.get_final_pdf_url')
def test_validate_url_failure(mock_get_final_pdf_url, processor):
    mock_get_final_pdf_url.return_value = (False, None, "Not a PDF URL")
    is_valid, error = processor._validate_url("http://example.com/page.html")
    assert is_valid is False
    assert error == "Not a PDF URL"

@patch('paper_processor.requests.get')
def test_download_pdf_success(mock_get, processor):
    # Mock the requests.get response
    mock_response = MagicMock()
    mock_response.iter_content = MagicMock(return_value=[b'test data'])
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    # Mock the open function to prevent actual file I/O
    with patch('builtins.open', new_callable=MagicMock) as mock_file:
        pdf_path = processor._download_pdf("http://example.com/paper.pdf")
        # Assert that the PDF path starts with '/fake/path'
        assert pdf_path.parent == Path('/fake/path')
        mock_get.assert_called_once_with("http://example.com/paper.pdf", stream=True)
        mock_response.raise_for_status.assert_called_once()
        # Assert that open was called with the correct file path and mode
        mock_file.assert_called_once_with(pdf_path, 'wb')

@patch('paper_processor.requests.get')
def test_download_pdf_failure(mock_get, processor):
    # Mock the requests.get to raise an exception
    mock_get.side_effect = Exception("Download failed")
    
    pdf_path = processor._download_pdf("http://example.com/paper.pdf")
    assert pdf_path is None

def test_list_processed_papers(processor):
    # Set the return value for load_master on the mock instance
    processor.metadata_manager.load_master.return_value = {
        "paper1": {
            "processing_date": "2024-01-01",
            "title": "Paper One"
        },
        "paper2": {
            "processing_date": "2024-02-01",
            "title": "Paper Two"
        }
    }
    papers = processor.list_processed_papers()
    assert len(papers) == 2
    assert papers[0]['title'] == "Paper Two"  # Newest first
    assert papers[1]['title'] == "Paper One"