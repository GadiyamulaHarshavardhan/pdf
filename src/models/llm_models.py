# src/models/llm_models.py
from typing import Dict, Any
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
import json
import re
import logging

logger = logging.getLogger(__name__)

class LLMModels:
    def __init__(self, config):
        self.config = config
        self.llm = Ollama(
            base_url=config.ollama_base_url,
            model=config.model_name,
            temperature=0.1
        )
        self.json_parser = JsonOutputParser()
        self.str_parser = StrOutputParser()
    
    def analyze_content_type(self, content: str, url: str = "") -> Dict[str, Any]:
        """Analyze content type and categorize with enhanced accuracy"""
        try:
            # Create a more detailed prompt for better analysis
            prompt = ChatPromptTemplate.from_template("""
            Analyze the following web content and determine:
            1. Content type (blog, documentation, academic, news, educational, research, etc.)
            2. Main topics/categories (be specific and detailed)
            3. Whether it contains downloadable documents (pdf, doc, ppt, xls, etc.)
            4. Relevance for document collection (0-10, where 10 is highly relevant)
            5. Potential document types that might be found on this page or linked pages
            
            Consider the URL if provided: {url}
            
            Content preview: {content}
            
            Return valid JSON format only:
            {{
                "content_type": "type",
                "categories": ["cat1", "cat2"],
                "has_documents": true/false,
                "relevance_score": 0-10,
                "potential_document_types": ["type1", "type2"],
                "reasoning": "brief explanation of why this content is relevant for document collection",
                "crawl_strategy": "recommended strategy for crawling this type of content (e.g., 'deep', 'broad', 'focused')"
            }}
            """)
            
            chain = prompt | self.llm | self.str_parser
            response = chain.invoke({
                "content": content[:3000] if content else "Empty content",  # Limit content size
                "url": url
            })
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # Validate and normalize the result
                if not isinstance(result.get("categories"), list):
                    result["categories"] = []
                if not isinstance(result.get("potential_document_types"), list):
                    result["potential_document_types"] = []
                if not isinstance(result.get("relevance_score"), int):
                    result["relevance_score"] = int(result.get("relevance_score", 0))
                
                return result
            else:
                logger.warning(f"Could not extract JSON from LLM response for URL: {url}")
                return {
                    "content_type": "unknown",
                    "categories": [],
                    "has_documents": False,
                    "relevance_score": 3,  # Default to medium relevance
                    "potential_document_types": [],
                    "reasoning": "Could not parse analysis",
                    "crawl_strategy": "broad"
                }
                
        except Exception as e:
            logger.error(f"Error in analyze_content_type: {e}")
            return {
                "content_type": "error",
                "categories": [],
                "has_documents": False,
                "relevance_score": 0,
                "potential_document_types": [],
                "reasoning": f"Analysis error: {str(e)}",
                "crawl_strategy": "broad"
            }
    
    def categorize_document(self, filename: str, content: str, url: str = "") -> str:
        """Categorize document based on filename, content, and URL with improved accuracy"""
        try:
            prompt = ChatPromptTemplate.from_template("""
            Categorize this document into one of these categories:
            - academic_papers (theses, research papers, scholarly articles)
            - technical_docs (manuals, specifications, technical guides)
            - business_documents (reports, contracts, proposals, financial docs)
            - legal_documents (laws, regulations, legal briefs)
            - educational_materials (textbooks, course materials, study guides)
            - reports (research reports, government reports, whitepapers)
            - presentations (slides, PowerPoint, Keynote files)
            - datasets (data files, statistics, spreadsheets)
            - multimedia (videos, audio, images with metadata)
            - source_code (programming files, scripts)
            - other (everything else)
            
            Consider the filename: {filename}
            Consider the URL: {url}
            Content preview: {content}
            
            Return only the category name, nothing else:
            """)
            
            chain = prompt | self.llm | self.str_parser
            category = chain.invoke({
                "filename": filename, 
                "content": content[:1000] if content else "No content available",  # Limit content size
                "url": url
            })
            
            # Validate the category
            valid_categories = [
                "academic_papers", "technical_docs", "business_documents", 
                "legal_documents", "educational_materials", "reports", 
                "presentations", "datasets", "multimedia", "source_code", "other"
            ]
            
            category = category.strip().lower()
            if category in valid_categories:
                return category
            else:
                logger.warning(f"Invalid category returned: {category}, defaulting to 'other'")
                return "other"
            
        except Exception as e:
            logger.error(f"Error in categorize_document: {e}")
            return "other"
    
    def extract_document_links_from_content(self, content: str, all_links: list) -> list:
        """Use AI to identify which links are most likely to contain documents"""
        try:
            # Create a prompt to analyze which links are most likely document links
            prompt = ChatPromptTemplate.from_template("""
            From the following list of links, identify which ones are most likely to contain downloadable documents (PDF, DOC, PPT, XLS, etc.).
            Consider the link text, URL structure, and context.
            
            Page content: {content}
            Links: {links}
            
            Return a list of the most promising document links (only the URLs):
            []
            """)
            
            # Limit the content and links to avoid overwhelming the model
            limited_content = content[:2000] if content else ""
            limited_links = all_links[:50]  # Limit to first 50 links
            
            chain = prompt | self.llm | self.str_parser
            response = chain.invoke({
                "content": limited_content,
                "links": str(limited_links)
            })
            
            # Extract the list of document links
            json_match = re.search(r'\[(.*?)\]', response, re.DOTALL)
            if json_match:
                # Try to parse as JSON
                try:
                    doc_links = json.loads(json_match.group())
                    if isinstance(doc_links, list):
                        return doc_links
                except:
                    # If JSON parsing fails, try to extract URLs with regex
                    urls = re.findall(r'https?://[^\s"\']+', response)
                    return urls
            else:
                # If no JSON array found, try to extract URLs from the response
                urls = re.findall(r'https?://[^\s"\']+', response)
                return urls
                
        except Exception as e:
            logger.error(f"Error in extract_document_links_from_content: {e}")
            return []
    
    def determine_crawl_strategy(self, content_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the best crawling strategy based on content analysis"""
        try:
            strategy = content_analysis.get("crawl_strategy", "broad")
            relevance_score = content_analysis.get("relevance_score", 5)
            
            # Adjust crawling parameters based on content type and relevance
            if strategy == "deep" or relevance_score >= 8:
                # For highly relevant content, go deeper
                return {
                    "max_depth": 3,
                    "max_links_per_page": 5,
                    "follow_links": True
                }
            elif strategy == "focused" or relevance_score >= 6:
                # For focused content, moderate depth but targeted links
                return {
                    "max_depth": 2,
                    "max_links_per_page": 3,
                    "follow_links": True
                }
            else:
                # For less relevant content, shallow and limited
                return {
                    "max_depth": 1,
                    "max_links_per_page": 2,
                    "follow_links": False
                }
                
        except Exception as e:
            logger.error(f"Error in determine_crawl_strategy: {e}")
            return {
                "max_depth": 2,
                "max_links_per_page": 3,
                "follow_links": True
            }