import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from openai_integration import OpenAIIntegration


class TestOpenAIIntegration(unittest.TestCase):
    def setUp(self):
        """
        SetUp: Initialize the OpenAIIntegration instance with a mocked assistant ID
        and patch the API key environment variable.
        """
        self.assistant_id = "mock_assistant_id"
        self.mock_api_key = patch('os.getenv', return_value="mock_api_key")
        self.mock_api_key.start()
        self.integration = OpenAIIntegration(self.assistant_id)

    def tearDown(self):
        """
        TearDown: Stop the patcher for os.getenv.
        """
        self.mock_api_key.stop()

    @patch('openai.OpenAI.beta.threads.create')
    @patch('openai.OpenAI.beta.threads.messages.create')
    def test_start_new_chat_success(self, mock_messages_create, mock_threads_create):
        """
        Test: Start a new chat thread successfully.
        Expected Results:
        - Thread is created and initial instructions are sent.
        """
        mock_thread = MagicMock(id="mock_thread_id")
        mock_threads_create.return_value = mock_thread

        result = self.integration.start_new_chat(num_chunks=5)
        self.assertTrue(result)
        self.assertEqual(self.integration.thread_id, "mock_thread_id")
        mock_messages_create.assert_called_once()


class TestOpenAIIntegration(unittest.TestCase):
    def setUp(self):
        """
        SetUp: Initialize the OpenAIIntegration instance with a mocked assistant ID.
        """
        self.assistant_id = "mock_assistant_id"
        self.integration = OpenAIIntegration(self.assistant_id)

    @patch('os.getenv', return_value="mock_api_key")
    def test_initialization_with_valid_api_key(self, mock_getenv):
        """
        Test: Initialization of OpenAIIntegration with a valid API key.
        Expected Results:
        - API key is retrieved from the environment.
        - Client is initialized successfully.
        """
        integration = OpenAIIntegration(self.assistant_id)
        self.assertEqual(integration.api_key, "mock_api_key")
        self.assertEqual(integration.assistant_id, self.assistant_id)

    @patch('os.getenv', return_value=None)
    def test_initialization_without_api_key(self, mock_getenv):
        """
        Test: Initialization fails if the API key is missing from the environment.
        Expected Results:
        - Raises ValueError due to missing API key.
        """
        with self.assertRaises(ValueError):
            OpenAIIntegration(self.assistant_id)

    @patch('openai.OpenAI.beta.threads.create')
    @patch('openai.OpenAI.beta.threads.messages.create')
    def test_start_new_chat_success(self, mock_messages_create, mock_threads_create):
        """
        Test: Start a new chat thread successfully.
        Expected Results:
        - Thread is created and initial instructions are sent.
        """
        mock_thread = MagicMock(id="mock_thread_id")
        mock_threads_create.return_value = mock_thread

        result = self.integration.start_new_chat(num_chunks=5)
        self.assertTrue(result)
        self.assertEqual(self.integration.thread_id, "mock_thread_id")
        mock_messages_create.assert_called_once()

    @patch('openai.OpenAI.beta.threads.create', side_effect=Exception("API error"))
    def test_start_new_chat_failure(self, mock_threads_create):
        """
        Test: Fail to start a new chat thread due to API error.
        Expected Results:
        - Returns False and logs the error.
        """
        result = self.integration.start_new_chat(num_chunks=5)
        self.assertFalse(result)
        self.assertIsNone(self.integration.thread_id)

    @patch('openai.OpenAI.beta.threads.messages.create')
    def test_send_chunk_success(self, mock_messages_create):
        """
        Test: Send a single chunk successfully.
        Expected Results:
        - Chunk is sent to the active thread.
        """
        self.integration.thread_id = "mock_thread_id"
        result = self.integration.send_chunk(chunk="Sample chunk text", chunk_num=1, total_chunks=3)
        self.assertTrue(result)
        mock_messages_create.assert_called_once()

    def test_send_chunk_without_thread(self):
        """
        Test: Fail to send a chunk when no thread is active.
        Expected Results:
        - Raises ValueError due to missing thread ID.
        """
        result = self.integration.send_chunk(chunk="Sample chunk text", chunk_num=1, total_chunks=3)
        self.assertFalse(result)

    @patch('openai.OpenAI.beta.threads.messages.list')
    @patch('openai.OpenAI.beta.threads.runs.create')
    @patch('openai.OpenAI.beta.threads.runs.retrieve')
    def test_request_summary_success(self, mock_run_retrieve, mock_run_create, mock_messages_list):
        """
        Test: Request and retrieve the final summary successfully.
        Expected Results:
        - Summary is returned after the run completes.
        """
        self.integration.thread_id = "mock_thread_id"

        # Mock the run process
        mock_run = MagicMock(id="mock_run_id")
        mock_run_create.return_value = mock_run
        mock_run_retrieve.side_effect = [
            MagicMock(status="processing"),
            MagicMock(status="completed")
        ]

        # Mock the summary retrieval
        mock_message = MagicMock(role="assistant", content=[MagicMock(text=MagicMock(value="[[Paper Summary]]"))])
        mock_messages_list.return_value.data = [mock_message]

        summary = self.integration.request_summary()
        self.assertEqual(summary, "[[Paper Summary]]")

    @patch('openai.OpenAI.beta.threads.runs.create', side_effect=Exception("API error"))
    def test_request_summary_failure(self, mock_run_create):
        """
        Test: Fail to retrieve the final summary due to API error.
        Expected Results:
        - Returns None and logs the error.
        """
        self.integration.thread_id = "mock_thread_id"
        summary = self.integration.request_summary()
        self.assertIsNone(summary)

    @patch('builtins.open', new_callable=MagicMock)
    def test_save_summary_success(self, mock_open):
        """
        Test: Save the summary to a file successfully.
        Expected Results:
        - File is written to the specified output path.
        """
        output_path = Path("mock_summary.txt")
        result = self.integration.save_summary(summary="[[Paper Summary]]", output_path=output_path)
        self.assertTrue(result)
        mock_open.assert_called_once_with(output_path, 'w', encoding='utf-8')
        mock_open().write.assert_called_once_with("[[Paper Summary]]")

    @patch('builtins.open', side_effect=Exception("File error"))
    def test_save_summary_failure(self, mock_open):
        """
        Test: Fail to save the summary due to a file write error.
        Expected Results:
        - Returns False and logs the error.
        """
        output_path = Path("mock_summary.txt")
        result = self.integration.save_summary(summary="[[Paper Summary]]", output_path=output_path)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
