# Document Renamer

A Python program that automatically extracts dates from document content and renames files with the extracted date prefix, providing a two-line summary for each file processed.

## Features

- **Smart Date Extraction**: Automatically finds and extracts dates from document content
- Renames files with format: `YYYY.MM.DD_OriginalFileName.ext`
- Provides a summary showing file type, size, and extracted date
- **Creates detailed summary document** with all processed files, their titles, and content previews
- Processes all files in a specified folder
- Supports dry-run mode to preview changes
- Handles duplicate names automatically
- Sanitizes filenames (removes invalid characters, replaces spaces with underscores)
- Skips hidden files and already processed files
- Prioritizes important dates (document dates, invoice dates) over secondary dates (due dates)

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