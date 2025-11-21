#!/usr/bin/env python3
"""
Dynamic Web Scraping Agent with multiple technologies (Selenium, Playwright, BeautifulSoup)
This agent will take the first link from a text file and perform dynamic scraping of all links
and anchors on the website, downloading PDFs and organizing them.
"""
import os
import re
import time
import json
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import List, Dict, Set, Tuple, Optional
import logging
from pathlib import Path

# Import Selenium if available
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Selenium not available. Install with: pip install selenium")

# Import Playwright if available
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright not available. Install with: pip install playwright")
    print("Also run: playwright install")

# Import undetected-chromedriver for stealth
try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False
    print("undetected-chromedriver not available. Install with: pip install undetected-chromedriver")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DynamicWebScraper:
    def __init__(self, base_url: str, max_depth: int = 2, delay: float = 1.0):
        self.base_url = base_url
        self.max_depth = max_depth
        self.delay = delay
        self.visited_urls: Set[str] = set()
        self.all_links: Set[str] = set()
        self.pdf_links: Set[str] = set()
        self.session = requests.Session()
        self.setup_session()
        
        # Create PDF directory
        self.pdf_dir = Path("pdfs")
        self.pdf_dir.mkdir(exist_ok=True)
        
        # Setup drivers if available
        self.selenium_driver = None
        self.playwright_context = None
        self.playwright_browser = None
        
    def setup_session(self):
        """Setup requests session with proper headers"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and belongs to the same domain"""
        try:
            parsed = urlparse(url)
            base_parsed = urlparse(self.base_url)
            
            # Check if it's a valid URL
            if not all([parsed.scheme, parsed.netloc]):
                return False
                
            # Optionally, restrict to same domain
            # return parsed.netloc == base_parsed.netloc
            
            # For now, accept any valid URL
            return True
        except Exception:
            return False

    def extract_links_bs4(self, html: str, base_url: str) -> List[str]:
        """Extract all links using BeautifulSoup"""
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        
        # Find all anchor tags with href
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            if self.is_valid_url(full_url):
                links.add(full_url)
        
        # Find other potential links
        for tag in soup.find_all(['img', 'script', 'link'], src=True):
            src = tag.get('src')
            if src:
                full_url = urljoin(base_url, src)
                if self.is_valid_url(full_url):
                    links.add(full_url)
        
        for tag in soup.find_all('form', action=True):
            action = tag.get('action')
            if action:
                full_url = urljoin(base_url, action)
                if self.is_valid_url(full_url):
                    links.add(full_url)
        
        return list(links)

    def get_page_content_selenium(self, url: str) -> Optional[str]:
        """Get page content using Selenium (for JavaScript-heavy sites)"""
        if not SELENIUM_AVAILABLE:
            return None
            
        try:
            if self.selenium_driver is None:
                if UNDETECTED_AVAILABLE:
                    # Use undetected-chromedriver for stealth
                    options = uc.ChromeOptions()
                    options.add_argument('--no-sandbox')
                    options.add_argument('--disable-dev-shm-usage')
                    options.add_argument('--disable-blink-features=AutomationControlled')
                    options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    options.add_experimental_option('useAutomationExtension', False)
                    self.selenium_driver = uc.Chrome(options=options)
                else:
                    # Use regular Chrome
                    options = Options()
                    options.add_argument('--headless')
                    options.add_argument('--no-sandbox')
                    options.add_argument('--disable-dev-shm-usage')
                    options.add_argument('--disable-blink-features=AutomationControlled')
                    self.selenium_driver = webdriver.Chrome(options=options)
                
                # Execute script to remove webdriver property
                self.selenium_driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info(f"Scraping with Selenium: {url}")
            self.selenium_driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.selenium_driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Scroll to load dynamic content
            self.selenium_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            self.selenium_driver.execute_script("window.scrollTo(0, 0);")
            
            return self.selenium_driver.page_source
            
        except Exception as e:
            logger.error(f"Selenium error for {url}: {e}")
            return None

    def get_page_content_playwright(self, url: str) -> Optional[str]:
        """Get page content using Playwright (for complex sites)"""
        if not PLAYWRIGHT_AVAILABLE:
            return None
            
        try:
            if self.playwright_context is None:
                self.playwright = sync_playwright().start()
                self.playwright_browser = self.playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                self.playwright_context = self.playwright_browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
                )
            
            logger.info(f"Scraping with Playwright: {url}")
            page = self.playwright_context.new_page()
            
            # Navigate to the page
            page.goto(url, wait_until="networkidle")
            
            # Wait for dynamic content and scroll
            page.wait_for_timeout(3000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            page.evaluate("window.scrollTo(0, 0)")
            
            content = page.content()
            page.close()
            
            return content
            
        except PlaywrightTimeoutError as e:
            logger.error(f"Playwright timeout for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Playwright error for {url}: {e}")
            return None

    def get_page_content_requests(self, url: str) -> Optional[str]:
        """Get page content using requests (for static content)"""
        try:
            logger.info(f"Scraping with Requests: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Requests error for {url}: {e}")
            return None

    def extract_all_links(self, url: str) -> List[str]:
        """Extract links using multiple methods (fallback approach)"""
        all_links = set()
        
        # Try Playwright first (best for dynamic content)
        if PLAYWRIGHT_AVAILABLE:
            content = self.get_page_content_playwright(url)
            if content:
                links = self.extract_links_bs4(content, url)
                all_links.update(links)
                logger.info(f"Found {len(links)} links with Playwright on {url}")
        
        # Then try Selenium
        if SELENIUM_AVAILABLE and not all_links:
            content = self.get_page_content_selenium(url)
            if content:
                links = self.extract_links_bs4(content, url)
                all_links.update(links)
                logger.info(f"Found {len(links)} links with Selenium on {url}")
        
        # Finally try requests (fallback for static content)
        if not all_links:
            content = self.get_page_content_requests(url)
            if content:
                links = self.extract_links_bs4(content, url)
                all_links.update(links)
                logger.info(f"Found {len(links)} links with Requests on {url}")
        
        return list(all_links)

    def is_pdf_url(self, url: str) -> bool:
        """Check if URL is a PDF file"""
        # Check file extension
        if url.lower().endswith('.pdf'):
            return True
        
        # Check if it contains PDF-related keywords
        pdf_indicators = ['pdf', 'download', 'file', 'document']
        if any(indicator in url.lower() for indicator in pdf_indicators):
            # Try HEAD request to check content type
            try:
                head_response = self.session.head(url, timeout=5)
                content_type = head_response.headers.get('content-type', '').lower()
                return 'pdf' in content_type or 'application/pdf' in content_type
            except:
                pass
        
        return False

    def download_pdf(self, url: str) -> bool:
        """Download PDF file"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Check if it's actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and 'application/pdf' not in content_type:
                # If it's HTML, check if it redirects to a PDF
                if 'text/html' in content_type:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    # Look for meta refresh or direct PDF links
                    meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
                    if meta_refresh:
                        content = meta_refresh.get('content', '')
                        if 'url=' in content:
                            new_url = content.split('url=')[1].split(';')[0]
                            new_url = urljoin(url, new_url)
                            return self.download_pdf(new_url)
            
            # Generate filename from URL
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename or '.' not in filename:
                filename = f"document_{len(self.pdf_links)}.pdf"
            elif not filename.lower().endswith('.pdf'):
                filename += '.pdf'
            
            # Clean filename
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            filepath = self.pdf_dir / filename
            
            # Ensure unique filename
            counter = 1
            original_filepath = filepath
            while filepath.exists():
                stem = original_filepath.stem
                suffix = original_filepath.suffix
                filepath = self.pdf_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Save the PDF
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded PDF: {filepath.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download PDF {url}: {e}")
            return False

    def crawl_url(self, url: str, depth: int = 0) -> None:
        """Recursively crawl a URL up to max_depth"""
        if depth > self.max_depth or url in self.visited_urls:
            return
        
        logger.info(f"Crawling (depth {depth}): {url}")
        self.visited_urls.add(url)
        
        # Extract all links from the current URL
        links = self.extract_all_links(url)
        
        for link in links:
            if link not in self.all_links:
                self.all_links.add(link)
                
                # Check if it's a PDF
                if self.is_pdf_url(link):
                    self.pdf_links.add(link)
                    logger.info(f"Found PDF: {link}")
                
                # Continue crawling if within depth limit
                if depth < self.max_depth:
                    self.crawl_url(link, depth + 1)
        
        # Add delay between requests
        time.sleep(self.delay)

    def organize_pdfs(self):
        """Organize downloaded PDFs by domain or category"""
        logger.info("Organizing PDFs...")
        
        # Create subdirectories based on domain
        for pdf_file in self.pdf_dir.glob("*.pdf"):
            # Extract domain from filename or create based on content if possible
            domain = urlparse(self.base_url).netloc.replace('www.', '')
            domain_dir = self.pdf_dir / domain
            domain_dir.mkdir(exist_ok=True)
            
            # Move PDF to domain directory
            new_path = domain_dir / pdf_file.name
            if not new_path.exists():  # Don't overwrite
                pdf_file.rename(new_path)
        
        logger.info(f"Organized PDFs in {self.pdf_dir}")

    def run(self):
        """Run the dynamic scraping process"""
        logger.info(f"Starting dynamic scraping for: {self.base_url}")
        logger.info(f"Max depth: {self.max_depth}, Delay: {self.delay}s")
        
        # Start crawling from the base URL
        self.crawl_url(self.base_url, 0)
        
        logger.info(f"Found {len(self.all_links)} total links")
        logger.info(f"Found {len(self.pdf_links)} PDF links")
        
        # Download all PDFs
        logger.info("Starting PDF downloads...")
        successful_downloads = 0
        
        for pdf_url in self.pdf_links:
            logger.info(f"Downloading: {pdf_url}")
            if self.download_pdf(pdf_url):
                successful_downloads += 1
        
        logger.info(f"Downloaded {successful_downloads} PDFs out of {len(self.pdf_links)} found")
        
        # Organize PDFs
        self.organize_pdfs()
        
        # Save results
        self.save_results(successful_downloads)
        
        # Close drivers
        self.cleanup()
        
        logger.info("Scraping completed!")
        return {
            "total_links_found": len(self.all_links),
            "pdf_links_found": len(self.pdf_links),
            "pdfs_downloaded": successful_downloads,
            "visited_urls": len(self.visited_urls)
        }

    def save_results(self, successful_downloads: int):
        """Save scraping results to a JSON file"""
        results = {
            "base_url": self.base_url,
            "max_depth": self.max_depth,
            "total_links_found": len(self.all_links),
            "pdf_links_found": len(self.pdf_links),
            "pdfs_downloaded": successful_downloads,
            "visited_urls_count": len(self.visited_urls),
            "visited_urls": list(self.visited_urls),
            "all_links": list(self.all_links),
            "pdf_links": list(self.pdf_links),
            "timestamp": time.time()
        }
        
        with open(f"scraping_results_{int(time.time())}.json", 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info("Results saved to scraping_results.json")

    def cleanup(self):
        """Clean up resources"""
        if self.selenium_driver:
            try:
                self.selenium_driver.quit()
            except:
                pass
        
        if self.playwright_browser:
            try:
                self.playwright_browser.close()
            except:
                pass
        
        if hasattr(self, 'playwright'):
            try:
                self.playwright.stop()
            except:
                pass


def main():
    """Main function to run the dynamic scraper"""
    # Read the first URL from input_urls.txt
    input_file = "input_urls.txt"
    
    if not os.path.exists(input_file):
        logger.error(f"Input file {input_file} not found!")
        return
    
    with open(input_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and line.startswith(('http://', 'https://'))]
    
    if not urls:
        logger.error("No valid URLs found in input file!")
        return
    
    # Take the first URL
    first_url = urls[0]
    logger.info(f"Using first URL from {input_file}: {first_url}")
    
    # Create and run the scraper
    scraper = DynamicWebScraper(
        base_url=first_url,
        max_depth=2,  # You can adjust this
        delay=1.0     # Delay between requests
    )
    
    results = scraper.run()
    
    # Print summary
    print("\n" + "="*60)
    print("DYNAMIC WEB SCRAPING RESULTS")
    print("="*60)
    print(f"Base URL: {first_url}")
    print(f"Total links found: {results['total_links_found']}")
    print(f"PDF links found: {results['pdf_links_found']}")
    print(f"PDFs downloaded: {results['pdfs_downloaded']}")
    print(f"Pages visited: {results['visited_urls']}")
    print("="*60)


if __name__ == "__main__":
    main()