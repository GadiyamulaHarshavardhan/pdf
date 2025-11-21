# src/utils/config_generator.py
import json
import os

def create_input_files():
    """Create sample input files for testing"""
    
    # Sample URLs for testing
    sample_urls = [
        "https://example.com/documents",
        "https://docs.python.org/3/tutorial/",
        "https://www.w3.org/TR/",
        "https://arxiv.org/list/cs/recent",
        "https://github.com/langchain-ai/langchain"
    ]
    
    # Create sample text file
    with open("input_urls.txt", "w") as f:
        for url in sample_urls:
            f.write(f"{url}\n")
    
    # Create sample JSON file
    with open("input_urls.json", "w") as f:
        json.dump(sample_urls, f, indent=2)
    
    # Create sample CSV file
    import csv
    with open("input_urls.csv", "w", newline='') as f:
        writer = csv.writer(f)
        for url in sample_urls:
            writer.writerow([url])
    
    print("Sample input files created:")
    print("- input_urls.txt")
    print("- input_urls.json")
    print("- input_urls.csv")

if __name__ == "__main__":
    create_input_files()