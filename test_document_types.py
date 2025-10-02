#!/usr/bin/env python3
"""
Quick test to show document type identification
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from document_renamer import DocumentRenamer

def test_document_types():
    """Test document type identification on demo files"""
    
    demo_dir = Path("demo_docs")
    if not demo_dir.exists():
        print("❌ Demo docs folder not found. Run demo_pdf_summary.py first.")
        return
    
    print("📋 Document Type Identification Test")
    print("=" * 50)
    
    renamer = DocumentRenamer(str(demo_dir))
    
    text_files = [f for f in demo_dir.glob("*.txt") if not f.name.startswith("2025")]
    md_files = [f for f in demo_dir.glob("*.md") if not f.name.startswith("2025")]
    
    test_files = text_files + md_files
    
    for file_path in sorted(test_files):
        doc_type = renamer.get_document_type_description(file_path)
        print(f"📄 {file_path.name}")
        print(f"   Type: {doc_type}")
        print()
    
    print("✅ Document type identification complete!")
    print("\nTypes detected include:")
    print("- Contract, Invoice, Meeting Notes")
    print("- Report, Research, Text Document")
    print("- Based on filename and content analysis")

if __name__ == "__main__":
    test_document_types()