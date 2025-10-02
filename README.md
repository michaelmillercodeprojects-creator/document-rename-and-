# Document Renamer with ChatGPT Summaries

A Python tool that renames documents with standardized date prefixes in `YYYY.MM.DD_` format and generates intelligent summaries using ChatGPT API. The tool extracts dates from filenames and organizes documents chronologically while creating comprehensive summaries.

## Features

- **Smart Date Extraction**: Extracts dates from various filename formats
- **Standardized Naming**: Renames files with `YYYY.MM.DD_` prefix format
- **AI-Powered Summaries**: Uses ChatGPT API to generate intelligent document summaries
- **Fallback Summaries**: Provides descriptive summaries when API is unavailable
- **Date Cleanup**: Remove redundant date patterns from filenames
- **Flexible Operation**: Dry-run mode, custom dates, and various options
- **Comprehensive Logging**: Detailed processing information and error handling

## Installation

### Requirements
- Python 3.6+
- `requests` library for ChatGPT API integration
- `reportlab` library for PDF summary generation
- **OCR and Document Processing Libraries** (for non-OCR'd documents):
  - `pytesseract` + `tesseract-ocr` for image OCR
  - `PyMuPDF` for PDF text extraction
  - `python-docx` for Word documents
  - `pandas` + `openpyxl` for Excel files
  - `Pillow` for image processing

### Setup
```bash
# Install Python dependencies
pip install requests reportlab pytesseract pillow PyMuPDF python-docx pandas openpyxl

# Install Tesseract OCR engine
# Ubuntu/Debian:
sudo apt install tesseract-ocr

# macOS:
brew install tesseract

# Windows:
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Or use Chocolatey: choco install tesseract

# The tool automatically detects Tesseract in common locations!

# Optional: Set up OpenAI API key for enhanced summaries
export OPENAI_API_KEY="your-api-key-here"
```

## Usage

### Basic Usage
```bash
# Rename files with date prefixes and create summaries
python document_renamer.py /path/to/documents

# Create comprehensive PDF summary without renaming files
python document_renamer.py /path/to/documents --summarize-only

# Use ChatGPT API for enhanced summaries
python document_renamer.py /path/to/documents --openai-api-key "your-api-key"

# Create AI-powered PDF summary without renaming
python document_renamer.py /path/to/documents --summarize-only --openai-api-key "your-api-key"

# Dry run to see what would happen
python document_renamer.py /path/to/documents --dry-run

# Remove date patterns from end of filenames
python document_renamer.py /path/to/documents --remove-dates
```

### Advanced Options
```bash
# Use specific default date
python document_renamer.py /path/to/documents --date 2024-01-15

# Don't extract dates from filenames, use default for all
python document_renamer.py /path/to/documents --no-extract --date 2024-01-15

# Skip summary document creation
python document_renamer.py /path/to/documents --no-summary
```

## ChatGPT Integration

When provided with an OpenAI API key, the tool generates intelligent summaries by:

1. **Text Files**: Reading content and asking ChatGPT to summarize the actual document content
2. **Binary/Scanned Files**: Using filename and file type information to generate descriptive summaries
3. **Fallback Mode**: Using built-in logic when API is unavailable or fails

### Benefits of ChatGPT Summaries
- More accurate content analysis
- Better handling of complex documents
- Intelligent interpretation of scanned/binary files
## OCR and Document Reading

The tool now supports **comprehensive document reading** including non-OCR'd files:

### 📄 Supported File Types:
- **Text Files**: .txt, .md, .csv, .json, .xml, .html, .log
- **PDF Files**: Both text-based and scanned PDFs (with OCR)
- **Image Files**: .jpg, .png, .gif, .bmp, .tiff (with OCR)
- **Word Documents**: .docx files
- **Excel Files**: .xlsx files

### 🔍 OCR Capabilities:
- **Automatic OCR**: Scanned PDFs and images are processed with Tesseract OCR
- **Smart Path Detection**: Automatically finds Tesseract in common installation locations
- **Cross-Platform**: Works on Windows, macOS, and Linux without manual configuration
- **Multiple Formats**: Works with all common image formats
- **Fallback Support**: Gracefully handles files when OCR libraries aren't available

### 🛠️ Tesseract Auto-Detection:
The tool automatically searches for Tesseract in these locations:
- **Windows**: `C:\Program Files\Tesseract-OCR\`, Chocolatey paths, Conda environments
- **macOS**: `/usr/local/bin/`, `/opt/homebrew/bin/`, Homebrew locations  
- **Linux**: `/usr/bin/`, `/usr/local/bin/`, Snap packages
- **Environment Variables**: `TESSERACT_PATH`, `TESSDATA_PREFIX`

No manual path configuration needed in most cases!

### 📊 Content Analysis:
- **Real Content**: Reads actual document text, not just filenames
- **Intelligent Summaries**: Extracts meaningful information from content
- **Multi-page Support**: Processes multiple pages of PDFs
- **Error Handling**: Continues processing even if some files can't be read

## PDF Summary Generation

The `--summarize-only` option creates a comprehensive PDF document that analyzes all files in a folder without renaming them. This is perfect for:

- **Document Review**: Getting an overview of all documents in a folder
- **Content Analysis**: Understanding what files contain without opening them
- **Report Generation**: Creating professional summaries for stakeholders
- **Archive Analysis**: Analyzing historical document collections

### PDF Summary Features:
- **Professional Layout**: Clean, organized PDF with proper formatting
- **Document Titles**: Extracted and formatted from filenames
- **File Details**: Type, size, and technical information
- **AI Summaries**: Intelligent content analysis (with ChatGPT API)
- **Statistics**: File type breakdown and folder analytics
- **No File Changes**: Documents remain completely untouched

### Sample PDF Content:
```
Document Analysis Summary
Generated: 2025-10-02 18:30:15
Folder: /path/to/documents
Files Analyzed: 5

1. Q4 Financial Report
   File: 2024.12.31_Q4_Financial_Report.pdf
   Type: PDF file, 2.3 MB
   Summary:
   1. This quarterly financial report analyzes company performance for Q4 2024.
   2. The document includes revenue breakdowns, expense analysis, and profit projections.
   3. Key metrics show 15% growth compared to previous quarter with improved margins.

2. Contract Agreement
   File: contract_agreement_2024.docx
   Type: DOCX file, 456 KB
   Summary:
   1. This is a legal contract document outlining service agreements between parties.
   2. The contract includes payment terms, deliverables, and compliance requirements.
   3. This agreement appears to be effective from 2024 with standard business terms.
```

## Summary Document

The program automatically creates a comprehensive summary document (`YYYY.MM.DD_Document_Processing_Summary.md`) that includes:

- **Document Titles**: Extracted from filenames with proper formatting
- **File Details**: Original name, new name, extracted date, file size and type
- **Content Previews**: First 200 characters of each document's content
- **Processing Statistics**: Files by year, error summary, and processing details

### Sample Summary Document Structure:

```markdown
# Document Processing Summary

**Generated:** 2025-10-02 17:22:59
**Folder:** `/path/to/documents`
**Files Processed:** 3
**Date Extraction:** Enabled

---

## 1. Meeting Minutes

**Original Name:** `Meeting Minutes.txt`
**New Name:** `2024.03.22_Meeting_Minutes.txt`
**Date Extracted:** 2024-03-22
**File Details:** .TXT file, 417 bytes

**Content Preview:**
```
Meeting Minutes

Date: 03/22/2024
Time: 2:00 PM - 3:30 PM
Location: Conference Room A
```

---

## Summary Statistics

- **Total Files Processed:** 3
- **Files by Year:**
  - 2024: 3 files
```

## Date Extraction

The program intelligently extracts dates from document content using priority-based patterns:

### High Priority Dates (preferred):
- `Invoice Date: 2024-01-15`
- `Document Date: January 15, 2024`
- `Report Date: 2024/01/15`
- `Meeting Date: Jan 15, 2024`
- `Date: 2024-01-15`

### Medium Priority Dates:
- `Last Updated: December 25, 2023`
- Standalone dates like `September 15, 2024` near the beginning of documents

### Low Priority Dates (avoided when better dates exist):
- `Due Date: 2024-02-15`
- `Next Meeting: March 29, 2024`
- `Deadline: 2024-03-30`

## Usage

### Basic Usage (with automatic date extraction)
```bash
python3 document_renamer.py /path/to/folder
```

### Dry Run (Preview Changes)
```bash
python3 document_renamer.py --dry-run /path/to/folder
```

### Disable Date Extraction (use current date for all files)
```bash
python3 document_renamer.py --no-extract /path/to/folder
```

### Custom Default Date (used when no date found in document)
```bash
python3 document_renamer.py --date 2025-12-25 /path/to/folder
```

### Disable Summary Document Creation
```bash
python3 document_renamer.py --no-summary /path/to/folder
```

### Help
```bash
python3 document_renamer.py --help
```

## Example Output

```
Processing 4 files in '/workspaces/document-rename-and-/test_documents' (extracted from document content)
================================================================================
Renamed: 2024.01.15_Invoice.csv
Summary: .CSV file, 309 bytes [Date extracted: 2024-01-15]

Renamed: 2024.09.15_Financial_Report.txt
Summary: .TXT file, 314 bytes [Date extracted: 2024-09-15]

Renamed: 2024.03.22_Meeting_Minutes.txt
Summary: .TXT file, 417 bytes [Date extracted: 2024-03-22]

Renamed: 2023.12.25_Project_Update.md
Summary: .MD file, 474 bytes [Date extracted: 2023-12-25]

================================================================================
OPERATION SUMMARY
================================================================================
Successfully processed: 4 files
Errors encountered: 0 files
Date extraction: Enabled

Processed files with extracted dates:
  Invoice.csv -> 2024.01.15_Invoice.csv [Date: 2024-01-15]
  Financial Report.txt -> 2024.09.15_Financial_Report.txt [Date: 2024-09-15]
  Meeting Minutes.txt -> 2024.03.22_Meeting_Minutes.txt [Date: 2024-03-22]
  Project Update.md -> 2023.12.25_Project_Update.md [Date: 2023-12-25]
```

## Supported Date Formats

The program recognizes various date formats:

- **Month Names**: `January 15, 2024`, `Jan 15, 2024`, `Dec 25, 2023`
- **Numeric Formats**: `2024-01-15`, `01/15/2024`, `2024/01/15`
- **Labeled Dates**: `Date: 2024-01-15`, `Invoice Date: Jan 15, 2024`
- **ISO Format**: `2024-01-15`

## File Naming Rules

- Date format: `YYYY.MM.DD` (e.g., 2024.01.15)
- Spaces in filenames are replaced with underscores
- Invalid characters are removed
- If a file with the new name already exists, a counter is added (e.g., `_1`, `_2`)
- Hidden files (starting with `.`) are skipped
- Already processed files (starting with date prefix) are skipped

## Requirements

- Python 3.6 or higher
- No external dependencies required (uses only standard library)