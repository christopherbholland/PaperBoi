import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from paper_processor import PaperProcessor


class TestPaperProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = PaperProcessor()

    @patch('requests.head')
    def test_validate_url_success(self, mock_head):
        mock_head.return_value = MagicMock(
            status_code=200, 
            headers={'content-type': 'application/pdf'},
            url='https://example.com/sample.pdf'
        )
        is_valid, error_message = self.processor._validate_url('https://example.com/sample.pdf')
        self.assertTrue(is_valid)
        self.assertIsNone(error_message)

    @patch('pdfplumber.open')
    def test_extract_text_from_pdf_success(self, mock_pdfplumber):
        mock_pdf = MagicMock()
        mock_pdf.pages = [
            MagicMock(extract_text=lambda: "This is a longer text for Page 1."),
            MagicMock(extract_text=lambda: "This is a longer text for Page 2.")
        ]
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf

        pdf_path = Path("dummy.pdf")
        result = self.processor._extract_text_from_pdf(pdf_path)
        self.assertEqual(result, "This is a longer text for Page 1.\nThis is a longer text for Page 2.")

    def test_create_chunks(self):
        text = "This is sentence one. This is sentence two. This is sentence three."
        chunks = self.processor._create_chunks(text, max_chars=25)
        expected_chunks = ["This is sentence one.", "This is sentence two.", "This is sentence three."]
        self.assertEqual(chunks, expected_chunks)


if __name__ == "__main__":
    unittest.main()
