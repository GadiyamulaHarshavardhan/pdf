# main.py
import logging
import json
import csv
import os
import sys
from typing import List, Dict, Any

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import Config
from tools.web_tools import WebScrapingTools
from models.llm_models import LLMModels
from agents.document_agents import DocumentAgents
from graph.document_graph import DocumentCollectionGraph
from utils.organizer import DocumentOrganizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutonomousDocumentAgent:
    def __init__(self):
        self.config = Config()
        self.web_tools = WebScrapingTools()
        self.llm_models = LLMModels(self.config)
        self.agents = DocumentAgents(self.llm_models, self.web_tools, self.config)
        self.organizer = DocumentOrganizer(self.config)
        
        # Initialize graph
        self.graph = DocumentCollectionGraph(
            self.agents, self.web_tools, self.llm_models, self.config
        )
        
        # Track overall progress
        self.overall_results = {
            "processed_urls": [],
            "total_documents": 0,
            "failed_urls": [],
            "categories_summary": {}
        }
    
    def load_links_from_file(self, file_path: str) -> List[str]:
        """Load links from various file formats"""
        links = []
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return links
        
        file_extension = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_extension == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    links = [line.strip() for line in f if line.strip()]
            
            elif file_extension == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        links = [item for item in data if isinstance(item, str)]
                    elif isinstance(data, dict):
                        links = [value for value in data.values() if isinstance(value, str)]
            
            elif file_extension == '.csv':
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        for cell in row:
                            if isinstance(cell, str) and cell.strip():
                                links.append(cell.strip())
            
            else:
                logger.warning(f"Unsupported file format: {file_extension}")
        
        except Exception as e:
            logger.error(f"Error loading links from {file_path}: {e}")
        
        # Filter valid URLs
        valid_links = []
        for link in links:
            if link.startswith(('http://', 'https://')):
                valid_links.append(link)
            else:
                logger.warning(f"Skipping invalid URL: {link}")
        
        logger.info(f"Loaded {len(valid_links)} valid links from {file_path}")
        return valid_links
    
    def load_links_from_folder(self, folder_path: str) -> List[str]:
        """Load links from all supported files in a folder"""
        all_links = []
        supported_extensions = ['.txt', '.json', '.csv']
        
        if not os.path.exists(folder_path):
            logger.error(f"Folder not found: {folder_path}")
            return all_links
        
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in supported_extensions:
                    links = self.load_links_from_file(file_path)
                    all_links.extend(links)
        
        # Remove duplicates
        unique_links = list(set(all_links))
        logger.info(f"Loaded {len(unique_links)} unique links from folder {folder_path}")
        return unique_links
    
    def process_single_url(self, url: str, max_depth: int = 2) -> Dict[str, Any]:
        """Process a single URL and return PDF-only results"""
        logger.info(f"Processing URL: {url}")
        
        try:
            # Use the graph's simple_crawl (PDF-only, hub-aware)
            results = self.graph.simple_crawl(url, max_depth)
            
            # Organize downloaded PDFs
            organized_results = self.organizer.organize_documents(
                results.get("downloaded_files", [])
            )
            
            # Update overall results
            self.overall_results["processed_urls"].append({
                "url": url,
                "documents_downloaded": len(organized_results),
                "status": "success"
            })
            self.overall_results["total_documents"] += len(organized_results)
            
            # Update categories summary
            for doc in organized_results:
                category = doc.get("category", "question_papers")  # Default to question_papers
                if category not in self.overall_results["categories_summary"]:
                    self.overall_results["categories_summary"][category] = 0
                self.overall_results["categories_summary"][category] += 1
            
            logger.info(f"Successfully processed {url}: {len(organized_results)} PDFs downloaded")
            
            return {
                "url": url,
                "status": "success",
                "documents_downloaded": len(organized_results),
                "organized_results": organized_results
            }
            
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            self.overall_results["processed_urls"].append({
                "url": url,
                "documents_downloaded": 0,
                "status": "failed",
                "error": str(e)
            })
            self.overall_results["failed_urls"].append(url)
            
            return {
                "url": url,
                "status": "failed",
                "error": str(e),
                "documents_downloaded": 0
            }
    
    def process_multiple_urls(self, urls: List[str], max_depth: int = 2, delay: float = 1.0):
        """Process multiple URLs one by one (PDF-only)"""
        import time
        
        total_urls = len(urls)
        results = []
        
        logger.info(f"Starting processing of {total_urls} URLs for PDF collection")
        
        for index, url in enumerate(urls, 1):
            logger.info(f"Processing URL {index}/{total_urls}: {url}")
            
            result = self.process_single_url(url, max_depth)
            results.append(result)
            
            # Save progress after each URL
            self.save_progress()
            
            # Add delay between requests
            if index < total_urls:
                logger.info(f"Waiting {delay} seconds before next request...")
                time.sleep(delay)
        
        logger.info(f"Completed processing all URLs. Total PDFs: {self.overall_results['total_documents']}")
        return results
    
    def save_progress(self):
        """Save current progress to a file"""
        os.makedirs(self.config.data_dir, exist_ok=True)
        progress_file = os.path.join(self.config.data_dir, "progress.json")
        
        try:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.overall_results, f, indent=2, ensure_ascii=False)
            logger.debug("Progress saved successfully")
        except Exception as e:
            logger.error(f"Error saving progress: {e}")
    
    def load_progress(self):
        """Load previous progress if exists"""
        progress_file = os.path.join(self.config.data_dir, "progress.json")
        
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    self.overall_results = json.load(f)
                logger.info("Previous progress loaded successfully")
            except Exception as e:
                logger.error(f"Error loading progress: {e}")
    
    def generate_report(self):
        """Generate a PDF-only summary report"""
        report = {
            "summary": {
                "total_urls_processed": len(self.overall_results["processed_urls"]),
                "total_pdfs_downloaded": self.overall_results["total_documents"],
                "successful_urls": len([u for u in self.overall_results["processed_urls"] if u.get("status") == "success"]),
                "failed_urls": len(self.overall_results["failed_urls"]),
                "categories": self.overall_results["categories_summary"]
            },
            "details": self.overall_results["processed_urls"]
        }
        
        # Save report
        os.makedirs(self.config.data_dir, exist_ok=True)
        report_file = os.path.join(self.config.data_dir, "final_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print("\n" + "="*60)
        print("PDF COLLECTION REPORT")
        print("="*60)
        print(f"Total URLs processed: {report['summary']['total_urls_processed']}")
        print(f"Successful URLs: {report['summary']['successful_urls']}")
        print(f"Failed URLs: {report['summary']['failed_urls']}")
        print(f"Total PDFs downloaded: {report['summary']['total_pdfs_downloaded']}")
        print("\nCategories:")
        for category, count in sorted(report['summary']['categories'].items()):
            print(f"  - {category}: {count} PDFs")
        print(f"\nDetailed report saved to: {report_file}")
        print("="*60)
        
        return report

def main():
    """Main function with command line interface for PDF-only collection"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Autonomous PDF Collection Agent (Academic Focus)')
    parser.add_argument('--input', '-i', required=True, 
                       help='Input file or folder containing URLs (txt, json, csv)')
    parser.add_argument('--depth', '-d', type=int, default=2,
                       help='Maximum depth for link following (default: 2)')
    parser.add_argument('--delay', '-w', type=float, default=1.0,
                       help='Delay between requests in seconds (default: 1.0)')
    parser.add_argument('--resume', '-r', action='store_true',
                       help='Resume from previous progress')
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = AutonomousDocumentAgent()
    
    # Load previous progress if resuming
    if args.resume:
        agent.load_progress()
    
    # Load links based on input type
    if os.path.isfile(args.input):
        links = agent.load_links_from_file(args.input)
    elif os.path.isdir(args.input):
        links = agent.load_links_from_folder(args.input)
    else:
        logger.error(f"Input path not found: {args.input}")
        return
    
    if not links:
        logger.error("No valid links found to process")
        return
    
    # Filter out already processed URLs if resuming
    if args.resume:
        processed_urls = [item['url'] for item in agent.overall_results['processed_urls']]
        new_links = [url for url in links if url not in processed_urls]
        skipped = len(links) - len(new_links)
        logger.info(f"Resuming: {len(new_links)} new URLs to process (skipped {skipped} already processed)")
        links = new_links
    
    # Process all links
    if links:
        agent.process_multiple_urls(
            urls=links,
            max_depth=args.depth,
            delay=args.delay
        )
        
        # Generate final report
        agent.generate_report()
    else:
        logger.info("No new URLs to process")

if __name__ == "__main__":
    main()