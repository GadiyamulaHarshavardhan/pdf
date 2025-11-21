# src/config/settings.py
import os
from typing import Dict, Any

class Config:
    def __init__(self):
        self.data_dir = "data"
        self.raw_dir = os.path.join(self.data_dir, "raw")
        self.processed_dir = os.path.join(self.data_dir, "processed")
        self.organized_dir = os.path.join(self.data_dir, "organized")
        
        # Ollama configuration - using a more capable model if available
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")  # Using a more capable model
        
        # LangChain configuration
        self.chunk_size = 1000
        self.chunk_overlap = 200
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self):
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.organized_dir, exist_ok=True)