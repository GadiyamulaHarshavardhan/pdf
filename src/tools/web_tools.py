# src/tools/web_tools.py
import requests
from bs4 import BeautifulSoup
import urllib.parse
from typing import List, Dict, Any
import logging
import time
import re
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning
import mimetypes

# Suppress only SSL warnings (keep others)
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

class WebScrapingTools:
    def __init__(self):
        self.session = requests.Session()
        
        # Retry strategy
        retry_strategy = Retry(
            total=2,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Realistic headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Academic relevance keywords
        self.relevance_keywords = {
            'question', 'paper', 'exam', 'syllabus', 'qp', 'model', 'previous', 'past',
            'year', 'download', 'file', 'document', 'pdf', 'result', 'marks', 'solution',
            'assignment', 'notes', 'academic', 'btech', 'mtech', 'mba', 'mca', 'pharmacy'
        }

    def extract_links(self, url: str) -> List[Dict[str, str]]:
        """Extract links, skip non-HTML/non-academic paths"""
        # Skip non-academic paths early
        skip_patterns = ['/wp-json/', '/feed/', 'oembed', 'embed', 'trackback',
                        '.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.ico']
        if any(p in url.lower() for p in skip_patterns):
            return []
        
        try:
            # Allow insecure SSL (for nagarjunauniversity-ac.in)
            response = self.session.get(url, timeout=15, allow_redirects=True, verify=False)
            response.raise_for_status()
            final_url = response.url
            
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            links = []
            
            all_elements = soup.find_all(['a', 'link', 'area'], href=True)
            all_elements.extend(soup.find_all(['img', 'source', 'script'], src=True))
            
            for element in all_elements:
                if element.name in ['a', 'link', 'area'] and element.get('href'):
                    href = element['href']
                elif element.name in ['img', 'source', 'script'] and element.get('src'):
                    href = element['src']
                else:
                    continue
                    
                absolute_url = urllib.parse.urljoin(final_url, href)
                
                if absolute_url.startswith(('javascript:', 'mailto:', 'tel:')):
                    continue
                
                link_text = ""
                if element.name in ['a', 'area']:
                    link_text = element.get_text(strip=True)
                elif element.name == 'img':
                    link_text = element.get('alt', '') or element.get('title', '')
                else:
                    link_text = element.get('title', '')
                
                links.append({
                    'url': absolute_url,
                    'text': link_text,
                    'source_url': final_url,
                    'element': element.name
                })
            
            # Remove duplicates
            seen = set()
            unique = []
            for link in links:
                if link['url'] not in seen:
                    seen.add(link['url'])
                    unique.append(link)
            return unique
            
        except Exception as e:
            logging.error(f"Error extracting links from {url}: {e}")
            return []

    def is_document_link(self, url: str) -> bool:
        """Detect PDF using URL pattern + HEAD request"""
        url_lower = url.lower()
        
        # 1. Direct .pdf
        if url_lower.endswith('.pdf'):
            return True
        
        # 2. Skip obviously non-PDF
        non_pdf_ext = ('.html', '.php', '.aspx', '.jsp', '.xml', '.json')
        if any(url_lower.endswith(ext) for ext in non_pdf_ext):
            return False
        
        # 3. Academic keywords in URL
        has_academic_signal = any(kw in url_lower for kw in self.relevance_keywords)
        if not has_academic_signal:
            return False
        
        # 4. Confirm with HEAD request
        try:
            head_resp = self.session.head(url, timeout=5, allow_redirects=True, verify=False)
            content_type = head_resp.headers.get('content-type', '').lower()
            if 'application/pdf' in content_type or 'octet-stream' in content_type:
                return True
        except:
            # If HEAD fails, trust the academic signal
            return True
            
        return False

    def is_document_hub_page(self, url: str, link_text: str = "") -> bool:
        """Detect hub pages with semantic matching"""
        combined = f"{url.lower()} {link_text.lower()}"
        score = sum(kw in combined for kw in self.relevance_keywords)
        return score >= 2  # Require at least 2 signals

    def download_document(self, url: str, save_path: str) -> bool:
        """Download and ensure it's a real PDF"""
        try:
            # Ensure .pdf extension
            if not save_path.lower().endswith('.pdf'):
                save_path += '.pdf'
            
            response = self.session.get(url, timeout=30, stream=True, allow_redirects=True, verify=False)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            is_pdf = 'application/pdf' in content_type or 'octet-stream' in content_type
            
            if not is_pdf:
                # If HTML, try to find real PDF link inside
                if 'text/html' in content_type:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        abs_url = urllib.parse.urljoin(response.url, href)
                        if self.is_document_link(abs_url):
                            return self.download_document(abs_url, save_path)
                return False
            
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)
            
            return os.path.exists(save_path) and os.path.getsize(save_path) > 1000  # >1KB
            
        except Exception as e:
            logging.error(f"PDF download failed {url}: {e}")
            return False

    def validate_url(self, url: str) -> bool:
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False