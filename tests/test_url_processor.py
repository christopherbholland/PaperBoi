import pytest
from unittest.mock import patch, MagicMock
from url_processor import URLProcessor

@patch("url_processor.requests.head")
def test_get_final_pdf_url(mock_head):
    """
    Test getting the final PDF URL.
    """
    # Mock successful response with a PDF content type
    mock_response = MagicMock()
    mock_response.url = "https://arxiv.org/pdf/2305.10601.pdf"
    mock_response.headers = {"content-type": "application/pdf"}
    mock_response.raise_for_status = MagicMock()
    mock_head.return_value = mock_response

    url = "https://arxiv.org/abs/2305.10601"
    success, final_url, error = URLProcessor.get_final_pdf_url(url)
    assert success is True
    assert final_url == "https://arxiv.org/pdf/2305.10601.pdf"
    assert error is None

    # Mock failure for a non-PDF URL
    mock_response.headers = {"content-type": "text/html"}
    mock_head.return_value = mock_response
    success, final_url, error = URLProcessor.get_final_pdf_url(url)
    assert success is False
    assert final_url is None
    assert "does not point to a PDF" in error

    # Mock request failure
    mock_head.side_effect = Exception("Request failed")
    success, final_url, error = URLProcessor.get_final_pdf_url(url)
    assert success is False
    assert final_url is None
    assert "Error processing URL" in error