#!/usr/bin/env python3
"""
Test Tesseract path detection
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from document_renamer import DocumentRenamer

def test_tesseract_detection():
    """Test Tesseract path detection functionality"""
    
    print("🔍 Tesseract Path Detection Test")
    print("=" * 50)
    
    renamer = DocumentRenamer(".")
    
    # Test the path configuration
    print("🔧 Testing Tesseract configuration...")
    renamer.configure_tesseract_path()
    
    # Try to get tesseract version if available
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract version: {version}")
        
        # Show the path being used
        tesseract_cmd = getattr(pytesseract.pytesseract, 'tesseract_cmd', 'tesseract')
        print(f"📍 Tesseract command: {tesseract_cmd}")
        
    except ImportError:
        print("❌ pytesseract not installed")
    except Exception as e:
        print(f"⚠️  Tesseract detection issue: {str(e)}")
    
    print("\n💡 Tesseract Installation Tips:")
    print("Windows:")
    print("  - Download from: https://github.com/UB-Mannheim/tesseract/wiki")
    print("  - Or use: choco install tesseract")
    print("  - Set TESSERACT_PATH environment variable if needed")
    print("\nmacOS:")
    print("  - Use: brew install tesseract")
    print("\nLinux:")
    print("  - Use: sudo apt install tesseract-ocr")
    print("  - Or: sudo yum install tesseract")
    
    print(f"\n🔍 The tool will automatically search these locations:")
    
    import platform
    system = platform.system().lower()
    
    if system == 'windows':
        paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\ProgramData\chocolatey\bin\tesseract.exe',
        ]
    elif system == 'darwin':
        paths = [
            '/usr/local/bin/tesseract',
            '/opt/homebrew/bin/tesseract',
            '/usr/bin/tesseract',
        ]
    else:
        paths = [
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/snap/bin/tesseract',
        ]
    
    for path in paths[:5]:  # Show first 5
        exists = "✅" if os.path.exists(path) else "❌"
        print(f"  {exists} {path}")

if __name__ == "__main__":
    test_tesseract_detection()