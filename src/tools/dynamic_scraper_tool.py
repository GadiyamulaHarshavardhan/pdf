"""
Dynamic Web Scraping Tool for Agentic AI System
This tool integrates with the existing architecture and provides dynamic scraping capabilities
using multiple technologies (Selenium, Playwright, BeautifulSoup).
"""
import os
import re
import time
import json
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import List, Dict, Set, Optional
import logging
from pathlib import Path

# Import optional dependencies with graceful fallback
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

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False

logger = logging.getLogger(__name__)


class DynamicWebScrapingTool:
    def __init__(self, config=None):
        self.config = config or {}
        self.session = requests.Session()
        self.setup_session()
        
        # Create PDF directory
        self.pdf_dir = Path(self.config.get("pdf_dir", "pdfs"))
        self.pdf_dir.mkdir(exist_ok=True)
        
        # Setup drivers if available
        self.selenium_driver = None
        self.playwright_context = None
        self.playwright_browser = None

    def setup_session(self):
        """Setup requests session with proper headers"""
        self.session.headers.update({
            'User-Agent': self.config.get(
                'user_agent', 
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc])
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
        
        # Find links in JavaScript (basic extraction)
        js_links = re.findall(r'(?:href|src|action|location\s*\.\s*(?:assign|replace))\s*=\s*[\'"]([^\'"]*)[\'"]', html)
        for js_link in js_links:
            full_url = urljoin(base_url, js_link)
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
                    if self.config.get('headless', True):
                        options.add_argument('--headless')
                    self.selenium_driver = uc.Chrome(options=options)
                else:
                    # Use regular Chrome
                    options = Options()
                    if self.config.get('headless', True):
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
                    headless=self.config.get('headless', True),
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                self.playwright_context = self.playwright_browser.new_context(
                    user_agent=self.config.get(
                        'user_agent',
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
                    )
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
        pdf_indicators = ['pdf', 'download', 'file', 'document', 'report', 'manual', 'guide', 'paper', 'article']
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
                filename = f"document_{int(time.time())}.pdf"
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

    def crawl_url(self, url: str, depth: int = 0, max_depth: int = 2, delay: float = 1.0, 
                  visited_urls: Set[str] = None, all_links: Set[str] = None, 
                  pdf_links: Set[str] = None) -> Dict[str, Set[str]]:
        """Recursively crawl a URL up to max_depth"""
        if visited_urls is None:
            visited_urls = set()
        if all_links is None:
            all_links = set()
        if pdf_links is None:
            pdf_links = set()
        
        if depth > max_depth or url in visited_urls:
            return {"visited": visited_urls, "links": all_links, "pdfs": pdf_links}
        
        logger.info(f"Crawling (depth {depth}): {url}")
        visited_urls.add(url)
        
        # Extract all links from the current URL
        links = self.extract_all_links(url)
        
        for link in links:
            if link not in all_links:
                all_links.add(link)
                
                # Check if it's a PDF
                if self.is_pdf_url(link):
                    pdf_links.add(link)
                    logger.info(f"Found PDF: {link}")
                
                # Continue crawling if within depth limit
                if depth < max_depth:
                    self.crawl_url(link, depth + 1, max_depth, delay, visited_urls, all_links, pdf_links)
        
        # Add delay between requests
        time.sleep(delay)
        
        return {"visited": visited_urls, "links": all_links, "pdfs": pdf_links}

    def organize_pdfs(self, base_url: str):
        """Organize downloaded PDFs by domain or category"""
        logger.info("Organizing PDFs...")
        
        # Create subdirectories based on domain
        domain = urlparse(base_url).netloc.replace('www.', '')
        domain_dir = self.pdf_dir / domain
        domain_dir.mkdir(exist_ok=True)
        
        # Move PDFs to domain directory
        for pdf_file in self.pdf_dir.glob("*.pdf"):
            if pdf_file.parent == self.pdf_dir:  # Only move files in root, not subdirs
                # Move PDF to domain directory
                new_path = domain_dir / pdf_file.name
                if not new_path.exists():  # Don't overwrite
                    pdf_file.rename(new_path)
        
        logger.info(f"Organized PDFs in {domain_dir}")

    def scrape_dynamic_website(self, start_url: str, max_depth: int = 2, delay: float = 1.0) -> Dict:
        """Main method to scrape a dynamic website and download PDFs"""
        logger.info(f"Starting dynamic scraping for: {start_url}")
        logger.info(f"Max depth: {max_depth}, Delay: {delay}s")
        
        # Start crawling from the start URL
        results = self.crawl_url(
            url=start_url,
            depth=0,
            max_depth=max_depth,
            delay=delay
        )
        
        visited_urls = results["visited"]
        all_links = results["links"]
        pdf_links = results["pdfs"]
        
        logger.info(f"Found {len(all_links)} total links")
        logger.info(f"Found {len(pdf_links)} PDF links")
        
        # Download all PDFs
        logger.info("Starting PDF downloads...")
        successful_downloads = 0
        
        for pdf_url in pdf_links:
            logger.info(f"Downloading: {pdf_url}")
            if self.download_pdf(pdf_url):
                successful_downloads += 1
        
        logger.info(f"Downloaded {successful_downloads} PDFs out of {len(pdf_links)} found")
        
        # Organize PDFs
        self.organize_pdfs(start_url)
        
        # Prepare results
        results = {
            "start_url": start_url,
            "max_depth": max_depth,
            "total_links_found": len(all_links),
            "pdf_links_found": len(pdf_links),
            "pdfs_downloaded": successful_downloads,
            "visited_urls_count": len(visited_urls),
            "visited_urls": list(visited_urls),
            "all_links": list(all_links),
            "pdf_links": list(pdf_links),
            "pdf_directory": str(self.pdf_dir.absolute()),
            "timestamp": time.time()
        }
        
        logger.info("Dynamic scraping completed!")
        return results

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

    def __del__(self):
        """Cleanup on destruction"""
        self.cleanup()