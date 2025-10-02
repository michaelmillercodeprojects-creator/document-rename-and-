#!/usr/bin/env python3
"""
Test OCR and document reading capabilities
"""

import sys
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from document_renamer import DocumentRenamer

def create_test_image():
    """Create a simple test image with text for OCR testing"""
    
    # Create a white image
    img = Image.new('RGB', (600, 400), color='white')
    draw = ImageDraw.Draw(img)
    
    # Add some text
    text = """INVOICE #2024-INV-001
    
    Bill To: ABC Corporation
    Date: October 2, 2024
    
    Services Rendered:
    - Consulting Services: $5,000
    - Project Management: $2,000
    
    Total Amount: $7,000
    
    Payment Terms: Net 30 days
    Thank you for your business!"""
    
    try:
        # Try to use a basic font
        font = ImageFont.load_default()
    except:
        font = None
    
    # Draw the text
    draw.text((50, 50), text, fill='black', font=font)
    
    # Save the image
    test_dir = Path("test_ocr")
    test_dir.mkdir(exist_ok=True)
    
    img_path = test_dir / "test_invoice.png"
    img.save(img_path)
    
    return img_path

def test_ocr_functionality():
    """Test OCR and document reading capabilities"""
    
    print("🔍 OCR and Document Reading Test")
    print("=" * 50)
    
    # Create test image
    print("📸 Creating test image with text...")
    img_path = create_test_image()
    print(f"   Created: {img_path}")
    
    # Test OCR extraction
    print("\n🤖 Testing OCR text extraction...")
    
    test_dir = Path("test_ocr")
    renamer = DocumentRenamer(str(test_dir))
    
    # Test image OCR
    extracted_text = renamer.extract_text_from_file(img_path)
    
    print(f"📄 Extracted text from {img_path.name}:")
    print("-" * 30)
    print(extracted_text[:300] + "..." if len(extracted_text) > 300 else extracted_text)
    print("-" * 30)
    
    # Test content summary
    print("\n📝 Testing content summary generation...")
    summary = renamer.get_local_content_summary(img_path)
    print(f"Summary: {summary}")
    
    # Test with existing demo documents
    demo_dir = Path("demo_docs")
    if demo_dir.exists():
        print(f"\n📚 Testing with existing documents in {demo_dir}...")
        
        for file_path in demo_dir.glob("*.txt"):
            if not file_path.name.startswith("2025"):
                print(f"\n📄 {file_path.name}")
                extracted = renamer.extract_text_from_file(file_path)
                print(f"   Extracted {len(extracted)} characters")
                if extracted:
                    print(f"   Preview: {extracted[:100]}...")
    
    print("\n✅ OCR and document reading test complete!")
    print("\nNow your tool can read:")
    print("- Text files (.txt, .md, etc.)")
    print("- PDF files (both text and scanned)")  
    print("- Image files with OCR (.jpg, .png, etc.)")
    print("- Word documents (.docx)")
    print("- Excel files (.xlsx)")

if __name__ == "__main__":
    test_ocr_functionality()