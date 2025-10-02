#!/usr/bin/env python3
"""
Example usage of the DocumentRenamer class
"""

from document_renamer import DocumentRenamer
from pathlib import Path

def example_usage():
    """Demonstrate how to use DocumentRenamer programmatically"""
    
    # Example 1: Process files with current date
    print("Example 1: Processing with current date")
    print("-" * 40)
    
    folder_path = "/workspaces/document-rename-and-/test_documents"
    renamer = DocumentRenamer(folder_path)
    
    # Check if there are files to process
    files = [f for f in Path(folder_path).iterdir() if renamer.is_valid_file(f)]
    if files:
        print(f"Found {len(files)} files to process:")
        for file in files:
            print(f"  - {file.name}")
        
        # Uncomment the next line to actually process the files
        # renamer.process_folder()
        
        print("\n(Files not processed - uncomment the line in the script to actually rename them)")
    else:
        print("No files to process (they may already be renamed)")
    
    print("\n" + "=" * 50)
    
    # Example 2: Process files with custom date
    print("Example 2: Processing with custom date (dry run)")
    print("-" * 40)
    
    try:
        custom_renamer = DocumentRenamer(folder_path, date_override="2024-12-25")
        print(f"Using custom date prefix: {custom_renamer.date_prefix}")
        
        # Run in dry-run mode to show what would happen
        custom_renamer.process_folder(dry_run=True)
        
    except ValueError as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 50)
    
    # Example 3: Show file validation rules
    print("Example 3: File validation rules")
    print("-" * 40)
    
    test_files = [
        ".hidden_file.txt",          # Hidden file - skipped
        "normal_file.txt",           # Normal file - processed
        "2025.10.02_already.txt",    # Already processed - skipped
        "folder",                    # Directory - skipped (if it exists)
    ]
    
    for filename in test_files:
        # Create a mock Path object for testing
        mock_path = Path(filename)
        is_valid = (
            not filename.startswith('.') and
            not filename.startswith('2025.10.02') and
            not filename == 'folder'  # Simulating directory check
        )
        status = "PROCESS" if is_valid else "SKIP"
        print(f"  {filename:<25} -> {status}")

if __name__ == "__main__":
    example_usage()