# src/agents/document_agents.py
from langchain_core.tools import Tool
from typing import List, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)

class DocumentAgents:
    def __init__(self, llm_models, web_tools, config):
        self.llm_models = llm_models
        self.web_tools = web_tools
        self.config = config
        self.tools = self._setup_tools()
    
    def _setup_tools(self) -> List[Tool]:
        return [
            Tool(name="extract_links", func=self.web_tools.extract_links, description="Extract links"),
            Tool(name="download_pdf", func=self._download_document_wrapper, description="Download PDF"),
            Tool(name="is_pdf_link", func=self.web_tools.is_document_link, description="Check if PDF"),
            Tool(name="is_academic_hub", func=lambda url: self.web_tools.is_document_hub_page(url, ""), description="Check academic hub")
        ]
    
    def _download_document_wrapper(self, url: str) -> bool:
        try:
            filename = url.split("/")[-1]
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
            save_path = os.path.join(self.config.raw_dir, filename)
            return self.web_tools.download_document(url, save_path)
        except Exception as e:
            logger.error(f"PDF download error: {e}")
            return False

    def autonomous_process(self, start_url: str, max_depth: int = 2) -> Dict[str, Any]:
        """
        Academic-focused PDF collection:
        - Skips result-only pages (e.g., /jntuh-results/)
        - Prioritizes syllabus/question paper hubs
        """
        visited_urls = set()
        results = {
            "start_url": start_url,
            "visited_urls": [],
            "downloaded_files": [],
            "errors": [],
            "total_links_found": 0
        }
        
        def is_result_only_page(url: str, link_text: str = "") -> bool:
            """Skip pages that ONLY show results (no PDFs)"""
            combined = f"{url.lower()} {link_text.lower()}"
            result_terms = {"result", "grade", "marks", "score", "rank", "status", "jntuhresults.in", "schools9", "manabadi"}
            academic_terms = {"question", "paper", "syllabus", "model", "qp", "blueprint", "pdf"}
            return any(rt in combined for rt in result_terms) and not any(at in combined for at in academic_terms)

        def process_url(url: str, current_depth: int):
            if current_depth > max_depth or url in visited_urls:
                return
                
            visited_urls.add(url)
            results["visited_urls"].append({"url": url, "depth": current_depth})
            logger.info(f"Processing: {url} (depth {current_depth})")
            
            try:
                links = self.web_tools.extract_links(url)
                results["total_links_found"] += len(links)
                
                # Download PDFs
                pdf_links = [link for link in links if self.web_tools.is_document_link(link['url'])]
                for link in pdf_links:
                    link_url = link['url']
                    if any(f.get('source_url') == link_url for f in results['downloaded_files']):
                        continue
                    if not self.web_tools.validate_url(link_url):
                        continue
                    
                    filename = link_url.split("/")[-1]
                    if not filename.lower().endswith('.pdf'):
                        filename += '.pdf'
                    save_path = os.path.join(self.config.raw_dir, filename)
                    
                    if self.web_tools.download_document(link_url, save_path):
                        # Smart categorization
                        text = f"{filename} {link_url} {link.get('text', '')}".lower()
                        if any(kw in text for kw in ['syllabus', 'cbcs', 'structure', 'regulation']):
                            category = "syllabus"
                        elif any(kw in text for kw in ['question', 'paper', 'model', 'qp', 'blueprint', 'sample']):
                            category = "question_papers"
                        else:
                            category = "educational_materials"
                        
                        results["downloaded_files"].append({
                            "filename": filename,
                            "path": save_path,
                            "source_url": link_url,
                            "original_url": url,
                            "depth_found": current_depth,
                            "category": category
                        })
                        logger.info(f"✅ Downloaded {category}: {filename}")
                
                # Follow academic hubs ONLY
                if current_depth < max_depth:
                    candidate_links = []
                    for link in links:
                        link_url = link['url']
                        link_text = link.get('text', '')
                        if (not link_url.startswith(('http://', 'https://')) or 
                            link_url in visited_urls or 
                            self.web_tools.is_document_link(link_url)):
                            continue
                        
                        # Skip result-only pages
                        if is_result_only_page(link_url, link_text):
                            continue
                        
                        # Prioritize academic hubs
                        if self.web_tools.is_document_hub_page(link_url, link_text):
                            candidate_links.append((link, 10))
                        elif any(kw in f"{link_url.lower()} {link_text.lower()}" 
                                for kw in self.web_tools.relevance_keywords):
                            candidate_links.append((link, 5))
                    
                    candidate_links.sort(key=lambda x: x[1], reverse=True)
                    for link, _ in candidate_links[:5]:
                        process_url(link['url'], current_depth + 1)
                        
            except Exception as e:
                results["errors"].append({"url": url, "error": str(e), "depth": current_depth})
                logger.error(f"❌ Error: {e}")
        
        process_url(start_url, 0)
        logger.info(f"✅ Completed: {len(results['downloaded_files'])} PDFs downloaded")
        return results

    def simple_download_agent(self, url: str) -> Dict[str, Any]:
        """Download PDFs from a single page"""
        try:
            if self.web_tools.is_document_link(url):
                filename = url.split("/")[-1]
                if not filename.lower().endswith('.pdf'):
                    filename += '.pdf'
                save_path = os.path.join(self.config.raw_dir, filename)
                if self.web_tools.download_document(url, save_path):
                    category = "question_papers" if "question" in filename.lower() else "syllabus"
                    return {
                        "status": "success",
                        "downloaded_files": [{"filename": filename, "path": save_path, "category": category}],
                        "message": "Direct PDF download"
                    }
            
            links = self.web_tools.extract_links(url)
            pdf_links = [link for link in links if self.web_tools.is_document_link(link['url'])]
            downloaded_files = []
            
            for link in pdf_links:
                link_url = link['url']
                filename = link_url.split("/")[-1]
                if not filename.lower().endswith('.pdf'):
                    filename += '.pdf'
                save_path = os.path.join(self.config.raw_dir, filename)
                if self.web_tools.download_document(link_url, save_path):
                    text = f"{filename} {link.get('text', '')}".lower()
                    category = "question_papers" if any(k in text for k in ['question', 'paper', 'model']) else "syllabus"
                    downloaded_files.append({"filename": filename, "path": save_path, "category": category})
                    logger.info(f"✅ Downloaded: {filename}")
            
            return {
                "status": "success",
                "downloaded_files": downloaded_files,
                "message": f"Downloaded {len(downloaded_files)} PDFs"
            }
        except Exception as e:
            logger.error(f"Simple agent error: {e}")
            return {"status": "error", "downloaded_files": []}

    def analyze_and_categorize_documents(self, downloaded_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Categorize using filename/text (no LLM dependency)"""
        categorized = []
        for file_info in downloaded_files:
            text = f"{file_info['filename']} {file_info.get('source_url', '')}".lower()
            if any(kw in text for kw in ['syllabus', 'cbcs', 'regulation']):
                category = "syllabus"
            elif any(kw in text for kw in ['question', 'paper', 'model', 'qp', 'blueprint']):
                category = "question_papers"
            else:
                category = "educational_materials"
            
            categorized.append({**file_info, "category": category, "analyzed": True})
        return categorized