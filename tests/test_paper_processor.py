import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import json
from paper_processor import PaperProcessor


class TestPaperProcessorExtended(unittest.TestCase):
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

    @patch('requests.get')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_pdf_success(self, mock_file, mock_get):
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b'PDF content']
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        pdf_path = self.processor._download_pdf('https://example.com/sample.pdf')

        # Check if the mocked file was written to
        mock_file.assert_called_once_with(pdf_path, 'wb')
        handle = mock_file()
        handle.write.assert_called()
        self.assertTrue(str(pdf_path).endswith(".pdf"))

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

    @patch('builtins.open', new_callable=mock_open)
    def test_save_to_master_file(self, mock_file):
        data = {"key": "value"}
        self.processor._save_to_master_file(data)

        # Get the file handle from mock_open
        handle = mock_file()
        # Combine all write calls into a single string
        written_content = ''.join(call.args[0] for call in handle.write.call_args_list)

        # Check if the final written content matches the expected JSON
        expected_content = json.dumps(data, indent=4)
        self.assertEqual(written_content, expected_content)

    @patch('builtins.open', new_callable=mock_open, read_data='{}')
    def test_load_master_file(self, mock_file):
        result = self.processor._load_master_file()
        self.assertEqual(result, {})
        mock_file.assert_called_once_with(self.processor.master_file, 'r', encoding='utf-8')

    def test_create_metadata(self):
        url = "https://example.com/sample.pdf"
        pdf_path = Path("dummy.pdf")
        num_chunks = 3
        title = "Sample Title"
        doi = "10.1234/example"

        metadata = self.processor._create_metadata(url, pdf_path, num_chunks, title, doi)
        self.assertEqual(metadata['original_filename'], pdf_path.name)
        self.assertEqual(metadata['summary_filename'], f"summary_{pdf_path.stem}.txt")
        self.assertEqual(metadata['original_url'], url)
        self.assertEqual(metadata['num_chunks'], num_chunks)
        self.assertEqual(metadata['title'], title)
        self.assertEqual(metadata['doi'], doi)


if __name__ == "__main__":
    unittest.main()
