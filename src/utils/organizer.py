# src/utils/organizer.py
import os
import shutil
from typing import List, Dict, Any
import json

class DocumentOrganizer:
    def __init__(self, config):
        self.config = config
    
    def organize_documents(self, categorized_files: List[Dict[str, Any]]):
        """Organize documents into category folders"""
        category_folders = {}
        
        for file_info in categorized_files:
            category = file_info.get("category", "uncategorized")
            
            if category not in category_folders:
                category_path = os.path.join(self.config.organized_dir, category)
                os.makedirs(category_path, exist_ok=True)
                category_folders[category] = category_path
            
            # Move file to category folder
            source_path = file_info["path"]
            filename = os.path.basename(source_path)
            dest_path = os.path.join(category_folders[category], filename)
            
            if os.path.exists(source_path):
                shutil.move(source_path, dest_path)
                file_info["organized_path"] = dest_path
        
        # Save metadata
        metadata_path = os.path.join(self.config.organized_dir, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(categorized_files, f, indent=2)
        
        return categorized_files