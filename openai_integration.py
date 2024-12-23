# openai_integration.py

import os
from openai import OpenAI
from typing import Optional
import logging
from pathlib import Path
import time

class OpenAIIntegration:
    """
    Handles OpenAI Assistants API interactions for the PaperProcessor.
    Uses a pre-configured assistant to process paper chunks and generate summaries.
    """
    
    def __init__(self, assistant_id: str):
        """
        Initialize OpenAI integration with API key from environment and specific assistant.
        
        Args:
            assistant_id (str): The ID of the pre-configured OpenAI assistant to use
            
        Raises:
            ValueError: If OPENAI_API_KEY is not found in environment
        """
        # Get API key from environment
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
            
        # Initialize OpenAI client
        self.client = OpenAI()
        
        # Store assistant ID
        self.assistant_id = assistant_id
        
        # Current thread ID
        self.thread_id = None
        
    def start_new_chat(self, num_chunks: int) -> bool:
        """
        Start a new thread with the assistant.
        
        Args:
            num_chunks (int): Total number of chunks to be processed
            
        Returns:
            bool: True if thread created successfully, False otherwise
        """
        try:
            # Create a new thread
            thread = self.client.beta.threads.create()
            self.thread_id = thread.id
            
            # Send initial instruction
            self.client.beta.threads.messages.create(
                thread_id=self.thread_id,
                role="user",
                content=f"You will receive {num_chunks} chunks of an academic paper. "
                        "Please wait for all chunks before providing a comprehensive summary. "
                        "Your summary should include the paper name in [[Name of paper]] format."
            )
            
            logging.info(f"Successfully created new thread: {self.thread_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error starting new thread: {str(e)}")
            return False
            
    def send_chunk(self, chunk: str, chunk_num: int, total_chunks: int) -> bool:
        """
        Send a single chunk to the assistant.
        
        Args:
            chunk (str): Text chunk to send
            chunk_num (int): Current chunk number
            total_chunks (int): Total number of chunks
            
        Returns:
            bool: True if chunk sent successfully, False otherwise
        """
        try:
            if not self.thread_id:
                raise ValueError("No active thread")
                
            # Format message with chunk information
            message = f"[Chunk {chunk_num}/{total_chunks}]\n\n{chunk}"
            
            # Send message to thread
            self.client.beta.threads.messages.create(
                thread_id=self.thread_id,
                role="user",
                content=message
            )
            
            logging.info(f"Successfully sent chunk {chunk_num}/{total_chunks}")
            return True
            
        except Exception as e:
            logging.error(f"Error sending chunk {chunk_num}: {str(e)}")
            return False
            
    def request_summary(self) -> Optional[str]:
        """
        Request final summary from the assistant after all chunks are processed.
        
        Returns:
            Optional[str]: Generated summary if successful, None otherwise
        """
        try:
            if not self.thread_id:
                raise ValueError("No active thread")
                
            # Request final summary
            self.client.beta.threads.messages.create(
                thread_id=self.thread_id,
                role="user",
                content="All chunks have been provided. Please generate a comprehensive summary following the format specified."
            )
            
            # Create and run the assistant
            run = self.client.beta.threads.runs.create(
                thread_id=self.thread_id,
                assistant_id=self.assistant_id
            )
            
            # Wait for completion
            while True:
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=self.thread_id,
                    run_id=run.id
                )
                
                if run_status.status == 'completed':
                    break
                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    raise RuntimeError(f"Run failed with status: {run_status.status}")
                    
                time.sleep(1)  # Wait before checking again
                
            # Get the assistant's response
            messages = self.client.beta.threads.messages.list(
                thread_id=self.thread_id
            )
            
            # Get the last assistant message
            for message in messages.data:
                if message.role == "assistant":
                    summary = message.content[0].text.value
                    
                    # Verify summary contains paper name in correct format
                    if "[[" not in summary or "]]" not in summary:
                        logging.warning("Summary missing paper name in [[Name]] format")
                        
                    return summary
                    
            return None
            
        except Exception as e:
            logging.error(f"Error generating summary: {str(e)}")
            return None
            
    def save_summary(self, summary: str, output_path: Path) -> bool:
        """
        Save the generated summary to a file.
        
        Args:
            summary (str): Generated summary text
            output_path (Path): Path to save the summary
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(summary)
            logging.info(f"Successfully saved summary to {output_path}")
            return True
        except Exception as e:
            logging.error(f"Error saving summary: {str(e)}")
            return False