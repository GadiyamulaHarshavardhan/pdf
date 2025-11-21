# Dynamic Web Scraping Agent System

This system provides an AI-powered dynamic web scraping pipeline with support for multiple technologies (Selenium, Playwright, BeautifulSoup). It uses LangChain, LangGraph, and Ollama to create an autonomous agent that can intelligently navigate websites, extract links and anchors, and download PDFs.

## Features

- **Multi-Technology Scraping**: Uses Playwright (primary), Selenium (fallback), and requests (static content) for comprehensive web scraping
- **Dynamic Content Handling**: Can handle JavaScript-heavy sites with proper rendering
- **PDF Detection & Download**: Automatically detects and downloads PDF files
- **Link Extraction**: Extracts all links, anchors, and other potential document sources
- **Organized Storage**: Organizes downloaded PDFs by domain in structured folders
- **Agentic AI Integration**: Integrates with LangGraph for intelligent decision-making
- **Stealth Browsers**: Uses undetected-chromedriver for anti-bot evasion
- **Comprehensive URL Discovery**: Finds URLs in JavaScript, HTML attributes, and various HTML elements

## Installation

1. Install dependencies:
   ```bash
   bash install_requirements.sh
   ```

2. Make sure you have Ollama running with a suitable model (e.g., llama3)

## Usage

### Basic Usage

```bash
# Run dynamic scraping on the first URL in input_urls.txt (default behavior)
python main.py

# Run with specific parameters
python main.py --input input_urls.txt --depth 2 --delay 1.0 --mode dynamic

# Run in PDF-only mode (original functionality)
python main.py --input input_urls.txt --mode pdf-only
```

### Command Line Options

- `--input` or `-i`: Input file containing URLs (default: input_urls.txt)
- `--depth` or `-d`: Maximum depth for link following (default: 2)
- `--delay` or `-w`: Delay between requests in seconds (default: 1.0)
- `--mode`: Scraping mode - 'dynamic' (with JS rendering) or 'pdf-only' (default: dynamic)

### Input File Format

The input file should contain one URL per line, starting with http:// or https://:

```
https://www.example.com/
https://www.another-site.org/
```

## Architecture

- `main.py`: Main entry point with command-line interface
- `dynamic_scraper.py`: Standalone dynamic scraper (alternative entry point)
- `src/tools/dynamic_scraper_tool.py`: Core dynamic scraping tool class
- `src/tools/web_tools.py`: Original static scraping tools
- `src/agents/`, `src/graph/`, `src/models/`: AI agent components

## How It Works

The dynamic scraper uses a multi-layered approach:

1. **Content Extraction**: Tries Playwright first for JavaScript-heavy sites, then Selenium, and finally regular requests
2. **Link Discovery**: Extracts links from HTML anchors, JavaScript, and various HTML attributes
3. **PDF Detection**: Uses file extensions, content-type headers, and AI analysis to identify PDFs
4. **Download & Organization**: Downloads PDFs and organizes them by domain in the `pdfs/` directory
5. **AI Integration**: Uses LLMs for intelligent link analysis and document categorization