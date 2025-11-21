# src/graph/document_graph.py
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("LangGraph not available, using fallback implementation")

from typing import Dict, Any, List
import logging
import re

logger = logging.getLogger(__name__)

class DocumentCollectionGraph:
    def __init__(self, agents, web_tools, llm_models, config):
        self.agents = agents
        self.web_tools = web_tools
        self.llm_models = llm_models
        self.config = config
        self.visited_urls = set()

    def process_url(self, url: str, max_depth: int = 2) -> Dict[str, Any]:
        """
        Use simple_crawl with academic-focused logic
        """
        logger.info("Using academic-focused simple_crawl (PDF-only)")
        return self.simple_crawl(url, max_depth)

    def simple_crawl(self, start_url: str, max_depth: int = 2) -> Dict[str, Any]:
        """
        Academic-focused crawl that prioritizes syllabus/question paper pages.
        Avoids result-only pages (e.g., /jntuh-results/).
        """
        visited = set()
        results = {
            "start_url": start_url,
            "visited_urls": [],
            "downloaded_files": [],
            "errors": []
        }

        def is_result_page(url: str, link_text: str = "") -> bool:
            """Detect pages that show results but don't contain PDFs"""
            combined = f"{url.lower()} {link_text.lower()}"
            result_keywords = {"result", "grade", "marks", "score", "rank", "status"}
            academic_keywords = {"question", "paper", "syllabus", "model", "qp"}
            # If it has result keywords but NO academic keywords → skip
            has_result = any(kw in combined for kw in result_keywords)
            has_academic = any(kw in combined for kw in academic_keywords)
            return has_result and not has_academic

        def crawl(url: str, depth: int):
            if depth > max_depth or url in visited:
                return

            # Skip non-academic paths early
            skip_patterns = ['/wp-json/', '/feed/', 'oembed', 'embed', 'trackback',
                            '.css', '.js', '.jpg', '.png', '.gif', 'contact', 'faculty']
            if any(p in url.lower() for p in skip_patterns):
                return

            visited.add(url)
            results["visited_urls"].append(url)
            logger.info(f"Crawling: {url} (depth: {depth})")

            try:
                links = self.web_tools.extract_links(url)
                logger.info(f"Found {len(links)} links")

                # Download PDFs
                pdf_links = [link for link in links if self.web_tools.is_document_link(link['url'])]
                for link in pdf_links:
                    link_url = link['url']
                    if any(f['source_url'] == link_url for f in results['downloaded_files']):
                        continue
                    if not self.web_tools.validate_url(link_url):
                        continue

                    filename = link_url.split("/")[-1]
                    if not filename.lower().endswith('.pdf'):
                        filename += '.pdf'
                    save_path = f"{self.config.raw_dir}/{filename}"

                    if self.web_tools.download_document(link_url, save_path):
                        try:
                            category = self.llm_models.categorize_document(filename, "", link_url)
                        except:
                            # Use URL/text to infer category
                            text = f"{filename} {link_url} {link.get('text', '')}".lower()
                            if any(kw in text for kw in ['syllabus', 'cbcs', 'structure']):
                                category = "syllabus"
                            elif any(kw in text for kw in ['question', 'paper', 'model', 'qp']):
                                category = "question_papers"
                            else:
                                category = "educational_materials"
                        
                        results["downloaded_files"].append({
                            "filename": filename,
                            "path": save_path,
                            "source_url": link_url,
                            "original_url": url,
                            "depth_found": depth,
                            "category": category
                        })
                        logger.info(f"✅ Downloaded PDF: {filename} ({category})")

                # Follow relevant links only
                if depth < max_depth:
                    candidate_links = []
                    for link in links:
                        link_url = link['url']
                        link_text = link.get('text', '')
                        if (not link_url.startswith(('http://', 'https://')) or 
                            link_url in visited or 
                            self.web_tools.is_document_link(link_url)):
                            continue

                        # Skip pure result pages (e.g., jntuh-results)
                        if is_result_page(link_url, link_text):
                            continue

                        # Prioritize academic hubs
                        if self.web_tools.is_document_hub_page(link_url, link_text):
                            candidate_links.append((link, 10))
                        elif any(kw in f"{link_url.lower()} {link_text.lower()}" 
                                for kw in self.web_tools.relevance_keywords):
                            candidate_links.append((link, 5))

                    # Sort and follow top 5
                    candidate_links.sort(key=lambda x: x[1], reverse=True)
                    for link, _ in candidate_links[:5]:
                        crawl(link['url'], depth + 1)

            except Exception as e:
                error_msg = f"Error crawling {url}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(f"❌ {error_msg}")

        crawl(start_url, 0)
        return results