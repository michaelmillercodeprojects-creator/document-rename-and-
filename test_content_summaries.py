#!/usr/bin/env python3
"""
Test content summary generation
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from document_renamer import DocumentRenamer

def test_content_summaries():
    """Test content summary generation on demo files"""
    
    demo_dir = Path("demo_docs")
    if not demo_dir.exists():
        print("❌ Demo docs folder not found. Run demo_pdf_summary.py first.")
        return
    
    print("📖 Content Summary Test")
    print("=" * 60)
    
    renamer = DocumentRenamer(str(demo_dir))
    
    # Test on the original text files (not the generated PDFs/summaries)
    test_files = [
        "contract_amendment_2024.txt",
        "invoice_2024_001.txt", 
        "meeting_notes_sept_15_2024.md",
        "quarterly_report_2024-Q3.txt",
        "research_paper_draft.txt"
    ]
    
    for filename in test_files:
        file_path = demo_dir / filename
        if file_path.exists():
            print(f"📄 {filename}")
            summary = renamer.get_local_content_summary(file_path)
            print(f"   Summary: {summary}")
            print()
    
    print("✅ Content summary test complete!")
    print("\nWith ChatGPT API, summaries would be even more sophisticated!")

if __name__ == "__main__":
    test_content_summaries()