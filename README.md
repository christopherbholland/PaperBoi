```                      ____        _ 
|  _ \ __ _ _ __   ___ _ __| __ )  ___ (_)
| |_) / _` | '_ \ / _ \ '__|  _ \ / _ \| |
|  __/ (_| | |_) |  __/ |  | |_) | (_) | |
|_|   \__,_| .__/ \___|_|  |____/ \___/|_|
           |_|                             
    📚 Read | 🤖 Process | 📝 Summarize

```
A system for automatically downloading, processing, and summarizing academic papers using OpenAI's APIs
```      
      📄
    ／📄＼
  ／📄👀📄＼
／_________＼
▔▔▔▔▔▔▔▔▔▔▔
   PaperBoi
```
Features

Download papers from URLs (including arXiv)
Process PDFs into chunks for AI analysis
Generate summaries using OpenAI's PaperBoi assistant
Store organized metadata and summaries
Handle various URL formats and redirects
Validate PDF content automatically

# Academic Paper Processing System

A Python system for automatically downloading, processing, and summarizing academic papers using OpenAI's APIs.

## Features

- Download papers from URLs (including arXiv)
- Process PDFs into chunks for AI analysis
- Generate summaries using OpenAI's PaperBoi assistant
- Store organized metadata and summaries
- Handle various URL formats and redirects
- Validate PDF content automatically

## Setup

1. Clone this repository:
```bash
git clone <your-repo-url>
cd paper-processor
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

5. Ensure the following directory structure exists:
```
paper-processor/
├── full_papers/        # Downloaded PDFs
├── paperboi_summaries/ # Generated summaries
├── metadata/          # Paper metadata
└── error_log/        # Error logs
```

## Usage

1. Run the main script:
```bash
python paper_processor.py
```

2. Enter a paper URL when prompted. The system accepts various formats:
   - Direct PDF links
   - arXiv URLs (e.g., "arxiv.org/abs/2305.10601")
   - URLs that redirect to PDFs

Example URLs:
```
https://arxiv.org/abs/2305.10601
https://arxiv.org/pdf/2305.10601.pdf
https://example.com/paper.pdf
```

3. The system will:
   - Download the PDF
   - Process it into chunks
   - Generate a summary
   - Save metadata
   - Store everything in the appropriate directories

## Project Structure

```
paper-processor/
├── paper_processor.py     # Main processing script
├── url_processor.py       # URL handling and validation
├── config.py             # Configuration and metadata classes
├── openai_integration.py # OpenAI API integration
├── requirements.txt      # Python dependencies
└── .env                 # Environment variables
```

## Configuration

The system uses several configuration options that can be modified in `config.py`:

- Chunk size for processing (default: 7500 characters)
- Directory structure
- Metadata format
- Logging settings

## Error Handling

- All errors are logged to `error_log/error_log_YYYYMMDD.log`
- The system handles:
  - Invalid URLs
  - Download failures
  - PDF processing errors
  - API failures
  - File system errors

## Dependencies

- pdfplumber: PDF text extraction
- requests: URL handling and downloads
- python-dotenv: Environment variable management
- openai: OpenAI API integration
- tqdm: Progress bars
- pathlib: File system operations
