# Autonomous Document Collection Agent

This is an advanced autonomous web scraping and document downloading system that uses AI to intelligently identify, analyze, and download documents from provided URLs. The system follows links to discover more documents and categorizes them automatically.

## Features

- **Autonomous Scraping**: Automatically follows links from main URLs to sub-URLs to find documents
- **AI-Powered Analysis**: Uses LLM to identify document links, analyze content, and determine crawling strategies
- **Multi-Format Support**: Downloads various document types (PDF, DOC, PPT, XLS, TXT, etc.)
- **Smart Categorization**: Automatically categorizes downloaded documents
- **Batch Processing**: Processes multiple URLs in batches
- **Robust Error Handling**: Comprehensive error handling and retry mechanisms
- **Progress Tracking**: Saves progress and allows resumption of interrupted downloads

## Architecture

- **Web Scraping Tools**: Enhanced scraping with JavaScript URL extraction, retry mechanisms, and content-type detection
- **LLM Models**: AI-powered content analysis, document identification, and categorization
- **Document Agents**: Autonomous agents that make intelligent decisions about crawling and downloading
- **Configuration**: Flexible configuration with environment variables support

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure Ollama is running with a compatible model (e.g., llama3.1:8b):
```bash
ollama run llama3.1:8b
```

3. Configure environment variables in `.env` file (or use the default settings)

## Usage

```bash
python main.py -i input_urls.txt -d 2 -w 1.0
```

Options:
- `-i, --input`: Input file or folder containing URLs (txt, json, csv)
- `-d, --depth`: Maximum depth for link following (default: 2)
- `-w, --delay`: Delay between requests in seconds (default: 1.0)
- `-r, --resume`: Resume from previous progress

## Input Formats

The system supports multiple input formats:

- **Text file** (.txt): One URL per line
- **JSON file** (.json): Array of URLs or object with URL values
- **CSV file** (.csv): URLs in any column

## Output Structure

```
data/
├── raw/              # Raw downloaded documents
├── processed/        # Processed documents
├── organized/        # Organized by category
│   └── [category]/   # Category-specific folders
├── progress.json     # Current progress (for resumption)
└── final_report.json # Final processing report
```

## Enhanced Capabilities

1. **AI-Enhanced Document Detection**:
   - Traditional extension-based detection
   - Content-type header analysis
   - AI-powered link analysis based on context
   - JavaScript URL extraction

2. **Intelligent Crawling Strategy**:
   - Dynamic depth adjustment based on content relevance
   - Smart link selection using AI
   - URL validation and filtering

3. **Robust Download System**:
   - Retry mechanisms with exponential backoff
   - Content-type verification
   - File integrity checks
   - Duplicate prevention

4. **Advanced Categorization**:
   - 10+ document categories
   - Filename, content, and URL-based classification
   - Confidence scoring

## Configuration

You can customize the system using environment variables in the `.env` file:

- `OLLAMA_BASE_URL`: URL for the Ollama API (default: http://localhost:11434)
- `OLLAMA_MODEL`: Model name to use (default: llama3.1:8b)

## Accuracy Improvements

The system achieves high accuracy through:

1. **Multi-layered document detection** (extension + content-type + AI analysis)
2. **Context-aware link identification** using LLM
3. **Adaptive crawling strategies** based on content analysis
4. **Comprehensive error handling** and retries
5. **Duplicate detection and prevention**
6. **URL validation** before processing

## Example Usage

Create an input file with URLs (input_urls.txt):
```
https://example.com/documents
https://docs.python.org/3/
https://arxiv.org/list/cs/recent
```

Run the system:
```bash
python main.py -i input_urls.txt -d 3 -w 2.0
```

This will:
- Process all URLs in the input file
- Follow links up to 3 levels deep
- Wait 2 seconds between requests (respectful crawling)
- Download documents and categorize them
- Generate a final report