#!/usr/bin/env python3
"""
Test script to demonstrate ChatGPT API integration
This script tests both fallback mode and API mode (if key provided)
"""

import sys
import os
from pathlib import Path

# Add current directory to path to import document_renamer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from document_renamer import DocumentRenamer

def test_summary_generation():
    """Test both fallback and ChatGPT summary generation"""
    
    # Create test file
    test_dir = Path("test_api")
    test_dir.mkdir(exist_ok=True)
    
    test_file = test_dir / "sample_contract_2024-03-15.pdf"
    test_file.write_text("Sample content for testing")
    
    print("=== Document Renamer ChatGPT Integration Test ===\n")
    
    # Test 1: Fallback mode (no API key)
    print("1. Testing Fallback Mode (no ChatGPT API):")
    print("-" * 50)
    
    renamer_fallback = DocumentRenamer(str(test_dir), use_file_dates=True, openai_api_key=None)
    fallback_summary = renamer_fallback.get_document_summary(test_file)
    
    print(f"File: {test_file.name}")
    print("Summary:")
    for i, sentence in enumerate(fallback_summary, 1):
        print(f"  {i}. {sentence}")
    
    print("\n" + "=" * 60 + "\n")
    
    # Test 2: ChatGPT mode (if API key provided)
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key:
        print("2. Testing ChatGPT API Mode:")
        print("-" * 50)
        
        renamer_api = DocumentRenamer(str(test_dir), use_file_dates=True, openai_api_key=api_key)
        api_summary = renamer_api.get_document_summary(test_file)
        
        print(f"File: {test_file.name}")
        print("ChatGPT Summary:")
        for i, sentence in enumerate(api_summary, 1):
            print(f"  {i}. {sentence}")
    else:
        print("2. ChatGPT API Test Skipped:")
        print("-" * 50)
        print("No OPENAI_API_KEY environment variable found.")
        print("To test ChatGPT integration, set your API key:")
        print("export OPENAI_API_KEY='your-key-here'")
        print("or run with: python document_renamer.py test_documents --openai-api-key 'your-key'")
    
    print("\n" + "=" * 60 + "\n")
    
    # Cleanup
    test_file.unlink()
    test_dir.rmdir()
    
    print("✅ Test completed successfully!")
    print("\nNext steps:")
    print("- Run with your actual documents: python document_renamer.py /path/to/documents")
    print("- Use ChatGPT API: python document_renamer.py /path/to/documents --openai-api-key 'your-key'")
    print("- Try dry run first: python document_renamer.py /path/to/documents --dry-run")

if __name__ == "__main__":
    test_summary_generation()