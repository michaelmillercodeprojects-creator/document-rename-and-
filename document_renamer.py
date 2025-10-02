#!/usr/bin/env python3
"""
Document Renamer - Renames documents with date prefix and provides summaries
"""

import os
import sys
import re
import json
import io
from datetime import datetime
from pathlib import Path
import argparse
import json


class DocumentRenamer:
    def __init__(self, folder_path, date_override=None, use_file_dates=True, openai_api_key=None):
        """
        Initialize the DocumentRenamer
        
        Args:
            folder_path (str): Path to the folder containing documents to rename
            date_override (str): Optional date override in YYYY-MM-DD format
            use_file_dates (bool): If True, extract dates from filenames
            openai_api_key (str): OpenAI API key for generating summaries
        """
        self.folder_path = Path(folder_path)
        self.use_file_dates = use_file_dates
        self.openai_api_key = openai_api_key
        
        if date_override:
            try:
                self.default_date = datetime.strptime(date_override, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Date override must be in YYYY-MM-DD format")
        else:
            self.default_date = datetime.now()
        
        self.processed_files = []
        self.errors = []
        
        # Common date patterns to search for in documents
        self.date_patterns = [
            # Full month names
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',
            # Abbreviated month names
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+(\d{1,2}),?\s+(\d{4})',
            # Various date formats
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY-MM-DD or YYYY/MM/DD
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # MM-DD-YYYY or MM/DD/YYYY
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2})',  # MM-DD-YY or MM/DD/YY
            # Date: format
            r'[Dd]ate:\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
            r'[Dd]ate:\s*(\d{4})[/-](\d{1,2})[/-](\d{1,2})',
            # ISO format
            r'(\d{4})-(\d{2})-(\d{2})',
        ]
    
    def extract_date_from_filename(self, file_path):
        """Extract date from filename if present"""
        filename = file_path.name
        found_dates = []
        
        # Common filename date patterns
        filename_patterns = [
            r'(\d{4})[._-](\d{1,2})[._-](\d{1,2})',  # YYYY-MM-DD, YYYY_MM_DD, YYYY.MM.DD
            r'(\d{1,2})[._-](\d{1,2})[._-](\d{4})',  # MM-DD-YYYY, MM_DD_YYYY, MM.DD.YYYY
            r'(\d{4})(\d{2})(\d{2})',                # YYYYMMDD
            r'(\d{2})(\d{2})(\d{4})',                # MMDDYYYY
        ]
        
        for pattern in filename_patterns:
            matches = re.finditer(pattern, filename)
            for match in matches:
                groups = match.groups()
                try:
                    if len(groups[0]) == 4:  # Year first
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    else:  # Month/day first
                        month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                    
                    if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100:
                        found_date = datetime(year, month, day)
                        found_dates.append(found_date)
                except (ValueError, IndexError):
                    continue
        
        return found_dates

    def extract_date_from_file(self, file_path):
        """
        Extract date from filename only
        
        Args:
            file_path (Path): Path to the file
            
        Returns:
            datetime: Extracted date from filename or default date if none found
        """
        filename = file_path.name
        found_dates = []
        
        # Common filename date patterns (in order of preference)
        filename_patterns = [
            # ISO format and similar
            (r'(\d{4})[._-](\d{1,2})[._-](\d{1,2})', 'ymd'),  # YYYY-MM-DD, YYYY_MM_DD, YYYY.MM.DD
            (r'(\d{4})(\d{2})(\d{2})', 'ymd'),                # YYYYMMDD
            # US format
            (r'(\d{1,2})[._-](\d{1,2})[._-](\d{4})', 'mdy'),  # MM-DD-YYYY, MM_DD_YYYY, MM.DD.YYYY
            (r'(\d{2})(\d{2})(\d{4})', 'mdy'),                # MMDDYYYY
            # Alternative formats
            (r'(\d{1,2})[._-](\d{4})', 'my'),                 # MM-YYYY (assume day 1)
            (r'(\d{4})[._-](\d{1,2})', 'ym'),                 # YYYY-MM (assume day 1)
        ]
        
        print(f"Analyzing filename: {filename}")
        
        for pattern, date_format in filename_patterns:
            matches = re.finditer(pattern, filename)
            for match in matches:
                groups = match.groups()
                try:
                    if date_format == 'ymd':  # Year-Month-Day
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    elif date_format == 'mdy':  # Month-Day-Year
                        month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                    elif date_format == 'my':  # Month-Year
                        month, year, day = int(groups[0]), int(groups[1]), 1
                    elif date_format == 'ym':  # Year-Month
                        year, month, day = int(groups[0]), int(groups[1]), 1
                    
                    # Validate date components
                    if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100:
                        found_date = datetime(year, month, day)
                        found_dates.append(found_date)
                        print(f"Found date {found_date.strftime('%Y-%m-%d')} in filename")
                except (ValueError, IndexError):
                    continue
        
        if found_dates:
            # Return the first valid date found (highest priority pattern)
            return found_dates[0]
        else:
            print(f"No dates found in filename, using default date")
            return self.default_date

    def extract_dates_from_content(self, file_path):
        """Extract dates from document content with priority weighting"""
        try:
            # Read file content with different encodings
            content = ""
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if not content:
                return self.default_date
            
            # Search for dates with priority weighting
            found_dates = []
            
            # Priority patterns (higher priority first)
            priority_patterns = [
                # Highest priority: specific creation/document date fields
                (r'(?i)(?:invoice\s+date|document\s+date|report\s+date|meeting\s+date|created):\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', 100, 'month_name'),
                (r'(?i)(?:invoice\s+date|document\s+date|report\s+date|meeting\s+date|created):\s*(\d{4})[/-](\d{1,2})[/-](\d{1,2})', 100, 'numeric_ymd'),
                (r'(?i)(?:invoice\s+date|document\s+date|report\s+date|meeting\s+date|created):\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 100, 'numeric_mdy'),
                
                # High priority: generic "Date:" at start of line or with context
                (r'(?i)(?:^|\n|\s)date:\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', 90, 'month_name'),
                (r'(?i)(?:^|\n|\s)date:\s*(\d{4})[/-](\d{1,2})[/-](\d{1,2})', 90, 'numeric_ymd'),
                (r'(?i)(?:^|\n|\s)date:\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 90, 'numeric_mdy'),
                
                # Medium-high priority: last updated field
                (r'(?i)(?:last\s+updated):\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', 80, 'month_name'),
                (r'(?i)(?:last\s+updated):\s*(\d{4})[/-](\d{1,2})[/-](\d{1,2})', 80, 'numeric_ymd'),
                (r'(?i)(?:last\s+updated):\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 80, 'numeric_mdy'),
                
                # Medium priority: standalone month names near beginning of document
                (r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})', 50, 'month_name'),
                
                # Lower priority: due dates and other secondary dates
                (r'(?i)(?:due\s+date|next\s+meeting|deadline):\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', 20, 'month_name'),
                (r'(?i)(?:due\s+date|next\s+meeting|deadline):\s*(\d{4})[/-](\d{1,2})[/-](\d{1,2})', 20, 'numeric_ymd'),
                (r'(?i)(?:due\s+date|next\s+meeting|deadline):\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 20, 'numeric_mdy'),
                
                # Lowest priority: numeric dates without context
                (r'(\d{4})-(\d{2})-(\d{2})', 10, 'numeric_ymd'),
                (r'(\d{1,2})/(\d{1,2})/(\d{4})', 5, 'numeric_mdy'),
            ]
            
            month_names = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            
            for pattern, priority, date_type in priority_patterns:
                matches = re.finditer(pattern, content)
                
                for match in matches:
                    try:
                        if date_type == 'month_name':
                            # Extract month name pattern
                            if priority >= 50:  # Patterns with labels or high priority
                                if priority >= 80:  # Highest priority patterns with labels
                                    date_text = match.group(1)
                                else:  # Standalone month patterns
                                    date_text = match.group(0)
                            else:  # Lower priority patterns
                                date_text = match.group(1) if len(match.groups()) > 0 else match.group(0)
                            
                            # Parse month name format
                            parts = date_text.strip().split()
                            if len(parts) >= 3:
                                month_name = parts[0].lower().replace(',', '')
                                if month_name in month_names:
                                    day = int(parts[1].replace(',', ''))
                                    year = int(parts[2])
                                    
                                    found_date = datetime(year, month_names[month_name], day)
                                    
                                    # Boost priority if found in first 200 characters
                                    pos_boost = 20 if match.start() < 200 else 0
                                    found_dates.append((found_date, priority + pos_boost))
                        
                        elif date_type == 'numeric_ymd':
                            groups = match.groups()
                            if len(groups) >= 3:
                                year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                                found_date = datetime(year, month, day)
                                
                                pos_boost = 20 if match.start() < 200 else 0
                                found_dates.append((found_date, priority + pos_boost))
                        
                        elif date_type == 'numeric_mdy':
                            groups = match.groups()
                            if len(groups) >= 3:
                                month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                                found_date = datetime(year, month, day)
                                
                                pos_boost = 20 if match.start() < 200 else 0
                                found_dates.append((found_date, priority + pos_boost))
                    
                    except (ValueError, IndexError):
                        continue
            
            # Return the highest priority date, or most recent if tied
            if found_dates:
                # Sort by priority (descending), then by date (descending)
                found_dates.sort(key=lambda x: (x[1], x[0]), reverse=True)
                return found_dates[0][0]
            else:
                return self.default_date
                
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return self.default_date

    def is_valid_file(self, file_path):
        """
        Check if the file should be processed
        
        Args:
            file_path (Path): Path to the file
            
        Returns:
            bool: True if file should be processed
        """
        # Skip hidden files, directories, and already renamed files
        if file_path.name.startswith('.'):
            return False
        if file_path.is_dir():
            return False
        # Skip files that already have date prefix pattern
        if re.match(r'^\d{4}\.\d{2}\.\d{2}_', file_path.name):
            return False
        
        return True
    
    def remove_date_from_filename(self, file_path):
        """
        Remove date patterns from the end of a filename (keeps YYYY.MM.DD_ prefix at beginning)
        
        Args:
            file_path (Path): Path to the file
            
        Returns:
            tuple: (success, old_name, new_name, error_message)
        """
        try:
            filename = file_path.name
            name_part = file_path.stem  # filename without extension
            extension = file_path.suffix
            
            # Patterns to remove from the end of filenames ONLY
            end_date_patterns = [
                r'[._-](\d{4})[._-](\d{1,2})[._-](\d{1,2})$',  # _YYYY-MM-DD, _YYYY_MM_DD, _YYYY.MM.DD at end
                r'[._-](\d{1,2})[._-](\d{1,2})[._-](\d{4})$',  # _MM-DD-YYYY, _MM_DD_YYYY, _MM.DD.YYYY at end
                r'[._-](\d{4})(\d{2})(\d{2})$',                # _YYYYMMDD at end
                r'[._-](\d{2})(\d{2})(\d{4})$',                # _MMDDYYYY at end
                r'[._-](\d{1,2})[._-](\d{4})$',                # _MM-YYYY at end
                r'[._-](\d{4})[._-](\d{1,2})$',                # _YYYY-MM at end
                # Note: Removed the beginning pattern - we want to KEEP YYYY.MM.DD_ prefixes
            ]
            
            new_name_part = name_part
            date_removed = False
            
            print(f"Analyzing filename for end date removal: {filename}")
            
            for pattern in end_date_patterns:
                match = re.search(pattern, new_name_part)
                if match:
                    print(f"Found end date pattern to remove: {match.group(0)}")
                    new_name_part = re.sub(pattern, '', new_name_part)
                    date_removed = True
                    break
            
            # Clean up any trailing separators
            new_name_part = new_name_part.rstrip('._-')
            
            if date_removed and new_name_part:
                new_filename = f"{new_name_part}{extension}"
                new_path = file_path.parent / new_filename
                
                # Check if new filename already exists
                if new_path.exists():
                    counter = 1
                    while new_path.exists():
                        new_filename = f"{new_name_part}_{counter}{extension}"
                        new_path = file_path.parent / new_filename
                        counter += 1
                
                # Rename the file
                file_path.rename(new_path)
                print(f"Removed end date from filename: {filename} -> {new_filename}")
                
                return True, filename, new_filename, None
            else:
                return False, filename, None, "No end date pattern found"
                
        except Exception as e:
            return False, file_path.name, None, str(e)

    def remove_dates_from_folder(self, dry_run=False):
        """
        Remove date patterns from all files in the folder
        
        Args:
            dry_run (bool): If True, show what would be done without actually renaming
        """
        if not self.folder_path.exists():
            print(f"Error: Folder '{self.folder_path}' does not exist.")
            return
        
        if not self.folder_path.is_dir():
            print(f"Error: '{self.folder_path}' is not a directory.")
            return
        
        # Get all files in the folder (don't use is_valid_file since we want to process all files)
        files = [f for f in self.folder_path.iterdir() if f.is_file() and not f.name.startswith('.')]
        
        if not files:
            print(f"No files to process in '{self.folder_path}'")
            return
        
        print(f"{'DRY RUN - ' if dry_run else ''}Removing dates from {len(files)} files in '{self.folder_path}'")
        print("=" * 80)
        
        processed_count = 0
        error_count = 0
        
        for file_path in files:
            if dry_run:
                # Show what would be done
                filename = file_path.name
                name_part = file_path.stem
                extension = file_path.suffix
                
                # Check for end date patterns (keep beginning YYYY.MM.DD_ prefixes)
                end_date_patterns = [
                    r'[._-](\d{4})[._-](\d{1,2})[._-](\d{1,2})$',
                    r'[._-](\d{1,2})[._-](\d{1,2})[._-](\d{4})$',
                    r'[._-](\d{4})(\d{2})(\d{2})$',
                    r'[._-](\d{2})(\d{2})(\d{4})$',
                    r'[._-](\d{1,2})[._-](\d{4})$',
                    r'[._-](\d{4})[._-](\d{1,2})$',
                    # Note: Not removing YYYY.MM.DD_ prefixes at beginning
                ]
                
                new_name_part = name_part
                date_found = False
                
                for pattern in end_date_patterns:
                    if re.search(pattern, new_name_part):
                        new_name_part = re.sub(pattern, '', new_name_part).rstrip('._-')
                        date_found = True
                        break
                
                if date_found and new_name_part:
                    new_filename = f"{new_name_part}{extension}"
                    print(f"Would rename: {filename}")
                    print(f"         to: {new_filename}")
                    print()
                else:
                    print(f"No date pattern found: {filename}")
                    print()
            else:
                # Actually remove dates
                success, old_name, new_name, error = self.remove_date_from_filename(file_path)
                
                if success:
                    print(f"✓ {old_name} -> {new_name}")
                    processed_count += 1
                else:
                    if "No end date pattern found" not in error:
                        print(f"✗ Error with '{old_name}': {error}")
                        error_count += 1
                    # Don't count "no end date pattern found" as an error
                print()
        
        if not dry_run:
            print("=" * 80)
            print("DATE REMOVAL SUMMARY")
            print("=" * 80)
            print(f"Files processed: {processed_count}")
            print(f"Errors encountered: {error_count}")

    def sanitize_filename(self, filename):
        """
        Sanitize filename by removing/replacing invalid characters
        
        Args:
            filename (str): Original filename
            
        Returns:
            str: Sanitized filename
        """
        # Replace spaces with underscores and remove problematic characters
        invalid_chars = '<>:"/\\|?*'
        sanitized = filename
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '')
        
        # Replace spaces with underscores
        sanitized = sanitized.replace(' ', '_')
        
        # Remove multiple consecutive underscores
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')
        
        return sanitized
    
    def get_file_summary(self, file_path):
        """
        Generate a brief summary of the file
        
        Args:
            file_path (Path): Path to the file
            
        Returns:
            str: Brief summary of the file
        """
        file_size = file_path.stat().st_size
        file_ext = file_path.suffix.upper()
        
        # Convert size to human readable format
        if file_size < 1024:
            size_str = f"{file_size} bytes"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
        
        return f"{file_ext} file, {size_str}"
    
    def rename_file(self, file_path):
        """
        Rename a single file with the date prefix extracted from content
        
        Args:
            file_path (Path): Path to the file to rename
            
        Returns:
            tuple: (success, old_name, new_name, error_message, extracted_date)
        """
        try:
            # Extract date from file content if enabled
            if self.use_file_dates:
                extracted_date = self.extract_date_from_file(file_path)
                date_prefix = extracted_date.strftime("%Y.%m.%d")
            else:
                extracted_date = self.default_date
                date_prefix = self.default_date.strftime("%Y.%m.%d")
            
            # Get the original filename without path
            original_name = file_path.stem
            file_extension = file_path.suffix
            
            # Sanitize the original name
            sanitized_name = self.sanitize_filename(original_name)
            
            # Create new filename with date prefix
            new_filename = f"{date_prefix}_{sanitized_name}{file_extension}"
            new_path = file_path.parent / new_filename
            
            # Check if new filename already exists
            if new_path.exists():
                counter = 1
                while new_path.exists():
                    new_filename = f"{date_prefix}_{sanitized_name}_{counter}{file_extension}"
                    new_path = file_path.parent / new_filename
                    counter += 1
            
            # Rename the file
            file_path.rename(new_path)
            
            return True, file_path.name, new_filename, None, extracted_date
            
        except Exception as e:
            return False, file_path.name, None, str(e), None
    
    def process_folder(self, dry_run=False, create_summary=True):
        """
        Process all files in the folder
        
        Args:
            dry_run (bool): If True, show what would be done without actually renaming
            create_summary (bool): If True, create a summary document after processing
        """
        if not self.folder_path.exists():
            print(f"Error: Folder '{self.folder_path}' does not exist.")
            return
        
        if not self.folder_path.is_dir():
            print(f"Error: '{self.folder_path}' is not a directory.")
            return
        
        # Get all files in the folder
        files = [f for f in self.folder_path.iterdir() if self.is_valid_file(f)]
        
        if not files:
            print(f"No files to process in '{self.folder_path}'")
            return
        
        date_source = "extracted from filenames" if self.use_file_dates else "using default/override date"
        print(f"{'DRY RUN - ' if dry_run else ''}Processing {len(files)} files in '{self.folder_path}' ({date_source})")
        print("=" * 80)
        
        for file_path in files:
            if dry_run:
                # Show what would be done
                if self.use_file_dates:
                    extracted_date = self.extract_date_from_file(file_path)
                    date_prefix = extracted_date.strftime("%Y.%m.%d")
                else:
                    extracted_date = self.default_date
                    date_prefix = self.default_date.strftime("%Y.%m.%d")
                
                original_name = file_path.stem
                sanitized_name = self.sanitize_filename(original_name)
                new_filename = f"{date_prefix}_{sanitized_name}{file_path.suffix}"
                summary = self.get_file_summary(file_path)
                
                print(f"Would rename: {file_path.name}")
                print(f"         to: {new_filename} ({summary}) [Date: {extracted_date.strftime('%Y-%m-%d')}]")
                print()
                
                # Store for potential summary creation
                self.processed_files.append((file_path.name, new_filename, extracted_date))
            else:
                # Actually rename the file
                success, old_name, new_name, error, extracted_date = self.rename_file(file_path)
                
                if success:
                    # Get summary of the renamed file
                    new_path = self.folder_path / new_name
                    summary = self.get_file_summary(new_path)
                    
                    print(f"Renamed: {new_name}")
                    print(f"Summary: {summary} [Date extracted: {extracted_date.strftime('%Y-%m-%d')}]")
                    print()
                    
                    self.processed_files.append((old_name, new_name, extracted_date))
                else:
                    print(f"Error renaming '{old_name}': {error}")
                    print()
                    self.errors.append((old_name, error))
        
        # Create summary document if requested and files were processed
        if create_summary and self.processed_files:
            summary_path = self.create_summary_document()
            if summary_path:
                print(f"{'DRY RUN - ' if dry_run else ''}Summary document created: {summary_path.name}")
                if dry_run:
                    print("(Summary document will be created during actual run)")
                print()
    
    def create_summary_document(self):
        """Create a summary document with all processed files and their 3-sentence summaries"""
        if not self.processed_files:
            return None
        
        summary_filename = f"{datetime.now().strftime('%Y.%m.%d')}_Document_Summary.md"
        summary_path = self.folder_path / summary_filename
        
        # Avoid overwriting existing summary
        counter = 1
        while summary_path.exists():
            summary_filename = f"{datetime.now().strftime('%Y.%m.%d')}_Document_Summary_{counter}.md"
            summary_path = self.folder_path / summary_filename
            counter += 1
        
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write("# Document Summary\n\n")
                f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Folder:** `{self.folder_path}`\n")
                f.write(f"**Files Processed:** {len(self.processed_files)}\n\n")
                f.write("---\n\n")
                
                for i, (old_name, new_name, extracted_date) in enumerate(self.processed_files, 1):
                    # Get file details
                    file_path = self.folder_path / new_name
                    if file_path.exists():
                        # Extract title from filename (remove date prefix and extension)
                        title_part = new_name
                        if re.match(r'^\d{4}\.\d{2}\.\d{2}_', title_part):
                            title_part = title_part[11:]  # Remove "YYYY.MM.DD_"
                        title_part = Path(title_part).stem  # Remove extension
                        title = title_part.replace('_', ' ')  # Convert underscores back to spaces
                        
                        f.write(f"## {title}\n\n")
                        f.write(f"**File:** `{new_name}`\n")
                        f.write(f"**Date:** {extracted_date.strftime('%Y-%m-%d')}\n\n")
                        
                        # Get 3-sentence summary
                        try:
                            summary_sentences = self.get_document_summary(file_path)
                            f.write(f"**Summary:**\n")
                            for j, sentence in enumerate(summary_sentences, 1):
                                f.write(f"{j}. {sentence}\n")
                            f.write("\n")
                        except Exception as e:
                            f.write(f"**Summary:** Unable to generate summary - {str(e)}\n\n")
                        
                        f.write("---\n\n")
                
                # Add statistics at the end
                f.write("## Summary Statistics\n\n")
                f.write(f"- **Total Documents:** {len(self.processed_files)}\n")
                
                # Group by year
                years = {}
                for _, _, date in self.processed_files:
                    year = date.year
                    years[year] = years.get(year, 0) + 1
                
                if years:
                    f.write(f"- **Documents by Year:**\n")
                    for year in sorted(years.keys()):
                        f.write(f"  - {year}: {years[year]} documents\n")
            
            return summary_path
            
        except Exception as e:
            print(f"Error creating summary document: {e}")
            return None
    
    def get_chatgpt_content_summary(self, file_path):
        """Use ChatGPT API to generate a concise content summary"""
        if not self.openai_api_key:
            return self.get_local_content_summary(file_path)
        
        try:
            import requests
        except ImportError:
            print("Warning: requests library not available. Install with: pip install requests")
            return self.get_local_content_summary(file_path)
        
        try:
            file_extension = file_path.suffix.lower()
            filename = file_path.stem
            
            # Remove date prefix from filename for cleaner analysis
            if re.match(r'^\d{4}\.\d{2}\.\d{2}_', filename):
                clean_filename = filename[11:]
            else:
                clean_filename = filename
            
            clean_filename = clean_filename.replace('_', ' ').replace('-', ' ')
            
            # Extract text content using our comprehensive extraction method
            content = self.extract_text_from_file(file_path)
            
            # Prepare prompt for ChatGPT - focused on content summary
            if content and len(content.strip()) > 50:
                prompt = f"""Read this document and provide a concise 2-3 sentence summary of what it's about and its main purpose or content.

Document: {clean_filename}

Content:
{content[:1500]}

Provide a brief, factual summary of what this document contains, its purpose, or what it discusses. Focus on the actual content, not file details."""
            else:
                # For non-text files or files we can't read
                prompt = f"""Based on the filename, provide a brief 1-2 sentence description of what this document likely contains.

Filename: {clean_filename}
File type: {file_extension.upper()}

Provide a concise description of what this document probably contains based on its name and type."""
            
            # Make API call to OpenAI
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': 120,  # Enough for 2-3 sentences
                'temperature': 0.3
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result['choices'][0]['message']['content'].strip()
                
                # Clean up the response
                summary = summary.replace('"', '').strip()
                
                if summary and len(summary) > 10:
                    return summary
                else:
                    return self.get_local_content_summary(file_path)
            
            else:
                print(f"OpenAI API error: {response.status_code}")
                return self.get_local_content_summary(file_path)
                
        except Exception as e:
            print(f"Error calling ChatGPT API: {e}")
            return self.get_local_content_summary(file_path)

    def extract_text_from_file(self, file_path):
        """Extract text from various file types including non-OCR'd documents"""
        file_extension = file_path.suffix.lower()
        content = ""
        
        try:
            # Text-based files
            if file_extension in {'.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm', '.log'}:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(2000)
                except Exception:
                    pass
            
            # Image files - use OCR
            elif file_extension in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif'}:
                try:
                    import pytesseract
                    from PIL import Image
                    
                    print(f"      🔍 Running OCR on image...")
                    image = Image.open(file_path)
                    content = pytesseract.image_to_string(image)[:2000]
                except ImportError:
                    print(f"      ⚠️  OCR unavailable: pip install pytesseract pillow")
                    content = ""
                except Exception as e:
                    print(f"      ⚠️  OCR failed: {str(e)}")
                    content = ""
            
            # PDF files - try multiple methods
            elif file_extension == '.pdf':
                # Method 1: Try PyMuPDF (fitz) for text extraction
                try:
                    import fitz  # PyMuPDF
                    print(f"      📄 Extracting text from PDF...")
                    doc = fitz.open(file_path)
                    text_content = ""
                    for page_num in range(min(3, len(doc))):  # First 3 pages
                        page = doc.load_page(page_num)
                        text_content += page.get_text()
                        if len(text_content) > 2000:
                            break
                    doc.close()
                    content = text_content[:2000]
                    
                    # If no text found, might be scanned PDF - try OCR
                    if len(content.strip()) < 50:
                        print(f"      🔍 PDF appears to be scanned, trying OCR...")
                        try:
                            import pytesseract
                            from PIL import Image
                            
                            # Convert PDF pages to images and OCR
                            doc = fitz.open(file_path)
                            ocr_text = ""
                            for page_num in range(min(2, len(doc))):  # First 2 pages for OCR
                                page = doc.load_page(page_num)
                                pix = page.get_pixmap()
                                img_data = pix.tobytes("ppm")
                                image = Image.open(io.BytesIO(img_data))
                                page_text = pytesseract.image_to_string(image)
                                ocr_text += page_text
                                if len(ocr_text) > 1500:
                                    break
                            doc.close()
                            content = ocr_text[:2000]
                        except ImportError:
                            print(f"      ⚠️  OCR unavailable for scanned PDF: pip install pytesseract pillow")
                        except Exception as e:
                            print(f"      ⚠️  PDF OCR failed: {str(e)}")
                            
                except ImportError:
                    print(f"      ⚠️  PDF reading unavailable: pip install PyMuPDF")
                    content = ""
                except Exception as e:
                    print(f"      ⚠️  PDF extraction failed: {str(e)}")
                    content = ""
            
            # Word documents
            elif file_extension in {'.doc', '.docx'}:
                try:
                    import docx
                    print(f"      📝 Extracting text from Word document...")
                    doc = docx.Document(file_path)
                    paragraphs = []
                    for paragraph in doc.paragraphs:
                        if paragraph.text.strip():
                            paragraphs.append(paragraph.text.strip())
                            if len(' '.join(paragraphs)) > 2000:
                                break
                    content = ' '.join(paragraphs)[:2000]
                except ImportError:
                    print(f"      ⚠️  Word document reading unavailable: pip install python-docx")
                    content = ""
                except Exception as e:
                    print(f"      ⚠️  Word document extraction failed: {str(e)}")
                    content = ""
            
            # Excel files
            elif file_extension in {'.xls', '.xlsx'}:
                try:
                    import pandas as pd
                    print(f"      📊 Reading Excel file...")
                    df = pd.read_excel(file_path, nrows=50)  # First 50 rows
                    # Convert to string representation
                    content = df.to_string()[:2000]
                except ImportError:
                    print(f"      ⚠️  Excel reading unavailable: pip install pandas openpyxl")
                    content = ""
                except Exception as e:
                    print(f"      ⚠️  Excel extraction failed: {str(e)}")
                    content = ""
            
            return content.strip()
            
        except Exception as e:
            print(f"      ⚠️  Text extraction error: {str(e)}")
            return ""
    def get_local_content_summary(self, file_path):
        """Generate a local content summary by reading the document"""
        try:
            filename = file_path.stem
            
            # Remove date prefix from filename for cleaner analysis
            if re.match(r'^\d{4}\.\d{2}\.\d{2}_', filename):
                clean_filename = filename[11:]
            else:
                clean_filename = filename
            
            clean_filename = clean_filename.replace('_', ' ').replace('-', ' ')
            
            # Extract text content using our comprehensive extraction method
            content = self.extract_text_from_file(file_path)
            
            if content and len(content.strip()) > 50:
                # Extract meaningful content for summary
                lines = content.split('\n')
                meaningful_lines = []
                
                for line in lines[:20]:  # Check first 20 lines
                    line = line.strip()
                    # Skip headers, dates, and very short lines
                    if (len(line) > 15 and 
                        not line.startswith('#') and 
                        not line.startswith('*') and
                        not line.startswith('-') and
                        not re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', line) and
                        not line.lower().startswith('date:') and
                        not line.lower().startswith('from:') and
                        not line.lower().startswith('to:')):
                        meaningful_lines.append(line)
                        if len(meaningful_lines) >= 3:
                            break
                
                if meaningful_lines:
                    # Create a summary from the meaningful content
                    summary_text = ' '.join(meaningful_lines[:2])
                    if len(summary_text) > 200:
                        summary_text = summary_text[:200] + "..."
                    
                    return f"This document discusses: {summary_text}"
            
            # Fallback for non-readable files or when content analysis fails
            doc_type = self.get_document_type_description(file_path).lower()
            return f"This appears to be a {doc_type} titled '{clean_filename.title()}'. Unable to extract readable text content for detailed analysis."
            
        except Exception as e:
            return f"Unable to analyze document content: {str(e)}"
        """Use ChatGPT API to identify document type"""
        if not self.openai_api_key:
            return self.get_document_type_description(file_path)
        
        try:
            import requests
        except ImportError:
            print("Warning: requests library not available. Install with: pip install requests")
            return self.get_document_type_description(file_path)
        
        try:
            file_extension = file_path.suffix.lower()
            filename = file_path.stem
            
            # Remove date prefix from filename for cleaner analysis
            if re.match(r'^\d{4}\.\d{2}\.\d{2}_', filename):
                clean_filename = filename[11:]
            else:
                clean_filename = filename
            
            clean_filename = clean_filename.replace('_', ' ').replace('-', ' ')
            
            # Try to read content for text files
            content = ""
            is_text_file = file_extension in {'.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm', '.log'}
            
            if is_text_file:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(1000)  # Read first 1000 chars
                except Exception:
                    pass
            
            # Prepare prompt for ChatGPT - focused on document type identification
            if content and len(content.strip()) > 50:
                prompt = f"""Based on the filename and content, identify what type of document this is in 1-3 words maximum.

Filename: {clean_filename}
File type: {file_extension.upper()}

Content preview:
{content[:800]}

Examples of good responses: "Invoice", "Meeting Notes", "Contract", "Transcript", "Email", "Report", "Research Paper", "Presentation", "Manual", "Policy Document"

Response (1-3 words only):"""
            else:
                # For non-text files or files we can't read
                prompt = f"""Based on the filename and file type, identify what type of document this likely is in 1-3 words maximum.

Filename: {clean_filename}
File type: {file_extension.upper()}

Examples of good responses: "Invoice", "Contract", "Report", "Presentation", "Image File", "Spreadsheet", "PDF Document"

Response (1-3 words only):"""
            
            # Make API call to OpenAI
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': 20,  # Very short response
                'temperature': 0.1  # Low temperature for consistent classification
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                doc_type = result['choices'][0]['message']['content'].strip()
                
                # Clean up the response
                doc_type = doc_type.replace('"', '').replace("'", '').strip()
                
                # Ensure it's title case and reasonable length
                if len(doc_type) <= 50 and doc_type:
                    return doc_type.title()
                else:
                    return self.get_document_type_description(file_path)
            
            else:
                print(f"OpenAI API error: {response.status_code}")
                return self.get_document_type_description(file_path)
                
        except Exception as e:
            print(f"Error calling ChatGPT API: {e}")
            return self.get_document_type_description(file_path)
        """Generate summary using ChatGPT API"""
        if not self.openai_api_key:
            return self.get_fallback_summary(file_path, max_sentences)
        
        try:
            import requests
        except ImportError:
            print("Warning: requests library not available. Install with: pip install requests")
            return self.get_fallback_summary(file_path, max_sentences)
        
        try:
            file_extension = file_path.suffix.lower()
            file_size = file_path.stat().st_size
            filename = file_path.stem
            
            # Remove date prefix from filename for cleaner title
            if re.match(r'^\d{4}\.\d{2}\.\d{2}_', filename):
                clean_filename = filename[11:]
            else:
                clean_filename = filename
            
            clean_filename = clean_filename.replace('_', ' ').replace('-', ' ')
            file_size_str = self.format_file_size(file_size)
            
            # Try to read content for text files
            content = ""
            is_text_file = file_extension in {'.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm', '.log'}
            
            if is_text_file:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(2000)  # Read first 2000 chars
                except Exception:
                    pass
            
            # Prepare prompt for ChatGPT
            if content and len(content.strip()) > 50:
                prompt = f"""Please provide exactly 3 sentences summarizing this document:

Filename: {clean_filename}
File type: {file_extension.upper()}
File size: {file_size_str}

Content preview:
{content[:1500]}

Please respond with exactly 3 sentences that describe what this document is about, its purpose, and key information. Do not include any other text or formatting."""
            else:
                # For non-text files or files we can't read
                prompt = f"""Please provide exactly 3 sentences describing this document based on its filename and file type:

Filename: {clean_filename}
File type: {file_extension.upper()}
File size: {file_size_str}

This appears to be a document that may be scanned, binary, or in a format that requires special software to read. Please provide 3 sentences describing what this document likely contains based on the filename and file type, its probable purpose, and what kind of information it might hold."""
            
            # Make API call to OpenAI
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': 200,
                'temperature': 0.3
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                summary_text = result['choices'][0]['message']['content'].strip()
                
                # Split into sentences and clean up
                sentences = []
                for delimiter in ['. ', '! ', '? ']:
                    parts = summary_text.split(delimiter)
                    if len(parts) > 1:
                        for i, part in enumerate(parts):
                            if part.strip():
                                sentences.append(part.strip() + (delimiter.strip() if i < len(parts)-1 and part != parts[-1] else ''))
                        break
                else:
                    # If no delimiters found, treat as single sentence
                    sentences = [summary_text]
                
                # Clean up and return up to max_sentences
                clean_sentences = []
                for sentence in sentences[:max_sentences]:
                    sentence = sentence.strip()
                    if sentence and len(sentence) > 5:
                        # Ensure sentence ends with punctuation
                        if not sentence[-1] in '.!?':
                            sentence += '.'
                        clean_sentences.append(sentence)
                
                if clean_sentences:
                    return clean_sentences
            
            else:
                print(f"OpenAI API error: {response.status_code} - {response.text}")
                return self.get_fallback_summary(file_path, max_sentences)
                
        except Exception as e:
            print(f"Error calling ChatGPT API: {e}")
            return self.get_fallback_summary(file_path, max_sentences)
    
    def get_fallback_summary(self, file_path, max_sentences=3):
        """Generate fallback summary when ChatGPT API is not available"""
        try:
            file_extension = file_path.suffix.lower()
            file_size = file_path.stat().st_size
            filename = file_path.stem
            
            # Try to read content for text-based files
            content = ""
            is_readable = False
            
            # Only attempt to read content for likely text files
            text_extensions = {'.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm', '.log'}
            
            if file_extension in text_extensions:
                encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
                
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read(500)  # Read first 500 chars to check if it's readable
                            # Check if content seems like text (not binary)
                            if len(content) > 20 and not any(ord(c) < 32 and c not in '\n\r\t' for c in content[:100]):
                                is_readable = True
                                break
                    except (UnicodeDecodeError, PermissionError):
                        continue
            
            # Generate summary based on available information
            if is_readable and content.strip():
                # For readable text files, try to extract meaningful content
                lines = content.split('\n')
                cleaned_lines = []
                
                for line in lines:
                    line = line.strip()
                    if len(line) > 10 and not line.startswith('#') and not line.startswith('*'):
                        if not any(keyword in line.lower() for keyword in ['date:', 'time:', 'location:']):
                            cleaned_lines.append(line)
                
                if cleaned_lines:
                    # Try to create content-based summary
                    summary_text = ' '.join(cleaned_lines[:3])
                    if len(summary_text) > 50:
                        sentences = []
                        for delimiter in ['. ', '! ', '? ']:
                            parts = summary_text.split(delimiter)
                            if len(parts) > 1:
                                for i, part in enumerate(parts[:max_sentences]):
                                    if part.strip():
                                        sentences.append(part.strip() + (delimiter.strip() if i < len(parts)-1 else ''))
                                break
                        
                        if sentences:
                            return sentences[:max_sentences]
            
            # For non-readable files or when content extraction fails, create descriptive summary
            file_size_str = self.format_file_size(file_size)
            
            # Extract meaningful information from filename
            filename_clean = filename.replace('_', ' ').replace('-', ' ')
            # Remove date prefix if present
            if re.match(r'^\d{4}\.\d{2}\.\d{2}\s+', filename_clean):
                filename_clean = filename_clean[11:].strip()
            
            # Generate summary based on file type and name
            if file_extension == '.pdf':
                summary_sentences = [
                    f"This is a PDF document titled '{filename_clean}' with a file size of {file_size_str}.",
                    f"The document appears to be a scanned or non-text-searchable PDF file.",
                    f"Content analysis requires OCR processing to extract readable text."
                ]
            elif file_extension in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}:
                summary_sentences = [
                    f"This is an image file titled '{filename_clean}' in {file_extension.upper()} format.",
                    f"The image has a file size of {file_size_str} and may contain document content.",
                    f"Text extraction would require OCR processing to analyze any textual content."
                ]
            elif file_extension in {'.doc', '.docx'}:
                summary_sentences = [
                    f"This is a Microsoft Word document titled '{filename_clean}' with a file size of {file_size_str}.",
                    f"The document may contain formatted text, images, and other elements.",
                    f"Advanced document parsing would be required to extract detailed content information."
                ]
            elif file_extension in {'.xls', '.xlsx'}:
                summary_sentences = [
                    f"This is a Microsoft Excel spreadsheet titled '{filename_clean}' with a file size of {file_size_str}.",
                    f"The spreadsheet likely contains tabular data, formulas, and calculations.",
                    f"Detailed analysis would require specialized Excel parsing to examine cell contents."
                ]
            elif file_extension in {'.ppt', '.pptx'}:
                summary_sentences = [
                    f"This is a Microsoft PowerPoint presentation titled '{filename_clean}' with a file size of {file_size_str}.",
                    f"The presentation likely contains slides with text, images, and multimedia elements.",
                    f"Content extraction would require specialized presentation parsing tools."
                ]
            else:
                # Generic file summary
                summary_sentences = [
                    f"This is a {file_extension.upper().replace('.', '')} file titled '{filename_clean}' with a file size of {file_size_str}.",
                    f"The file format may require specialized software or tools for content analysis.",
                    f"Manual review of the document would be needed to determine specific content details."
                ]
            
            return summary_sentences[:max_sentences]
            
        except Exception as e:
            return [
                f"Error analyzing document: {str(e)}",
                "The file may be corrupted, inaccessible, or in an unsupported format.",
                "Manual review of the document is recommended."
            ]

    def format_file_size(self, size_bytes):
        """Format file size in human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def get_document_type_description(self, file_path):
        """Generate a concise description of what type of document this is"""
        try:
            file_extension = file_path.suffix.lower()
            filename = file_path.stem
            
            # Remove date prefix from filename for cleaner analysis
            if re.match(r'^\d{4}\.\d{2}\.\d{2}_', filename):
                clean_filename = filename[11:]
            else:
                clean_filename = filename
            
            clean_filename = clean_filename.lower().replace('_', ' ').replace('-', ' ')
            
            # Try to read content for text files to get better classification
            content = ""
            is_text_file = file_extension in {'.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm', '.log'}
            
            if is_text_file:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(1000).lower()  # Read first 1000 chars
                except Exception:
                    pass
            
            # Analyze filename and content to determine document type
            filename_indicators = {
                'transcript': ['transcript', 'transcription', 'recording', 'interview', 'call', 'conversation'],
                'contract': ['contract', 'agreement', 'terms', 'service agreement', 'nda', 'legal'],
                'invoice': ['invoice', 'bill', 'receipt', 'payment', 'billing'],
                'report': ['report', 'analysis', 'quarterly', 'annual', 'financial', 'summary'],
                'meeting notes': ['meeting', 'notes', 'minutes', 'agenda', 'discussion'],
                'email': ['email', 'message', 'correspondence', 'reply', 'forward'],
                'proposal': ['proposal', 'quote', 'estimate', 'bid', 'rfp'],
                'presentation': ['presentation', 'slides', 'deck', 'powerpoint'],
                'manual': ['manual', 'guide', 'instructions', 'how to', 'tutorial'],
                'policy': ['policy', 'procedure', 'guidelines', 'rules', 'standards'],
                'letter': ['letter', 'correspondence', 'memo', 'memorandum'],
                'form': ['form', 'application', 'questionnaire', 'survey'],
                'specification': ['spec', 'specification', 'requirements', 'technical'],
                'checklist': ['checklist', 'todo', 'tasks', 'action items'],
                'research': ['research', 'study', 'paper', 'thesis', 'findings'],
                'marketing': ['marketing', 'brochure', 'flyer', 'advertisement', 'promo'],
                'resume': ['resume', 'cv', 'curriculum vitae', 'bio'],
                'budget': ['budget', 'financial plan', 'expenses', 'costs'],
                'calendar': ['calendar', 'schedule', 'timeline', 'dates'],
                'log': ['log', 'activity', 'history', 'record']
            }
            
            content_indicators = {
                'transcript': ['speaker:', 'interviewer:', 'timestamp:', '[music]', '[inaudible]', 'mm-hmm', 'uh-huh'],
                'meeting notes': ['agenda', 'attendees:', 'action items', 'next meeting', 'decisions made'],
                'email': ['from:', 'to:', 'subject:', 'dear', 'best regards', 'sincerely'],
                'contract': ['whereas', 'party', 'agreement', 'terms and conditions', 'signature'],
                'invoice': ['invoice number', 'due date', 'amount due', 'billing', 'payment terms'],
                'report': ['executive summary', 'findings', 'recommendations', 'conclusion', 'methodology'],
                'financial': ['revenue', 'profit', 'expenses', 'budget', 'financial', 'accounting'],
                'technical': ['function', 'parameter', 'algorithm', 'implementation', 'code', 'system'],
                'legal': ['plaintiff', 'defendant', 'court', 'jurisdiction', 'statute', 'whereas'],
                'medical': ['patient', 'diagnosis', 'treatment', 'symptoms', 'medical', 'doctor'],
                'academic': ['abstract', 'methodology', 'literature review', 'bibliography', 'thesis']
            }
            
            # Check filename for type indicators
            doc_type = "document"
            confidence = 0
            
            for doc_category, keywords in filename_indicators.items():
                matches = sum(1 for keyword in keywords if keyword in clean_filename)
                if matches > confidence:
                    confidence = matches
                    doc_type = doc_category
            
            # Check content for additional indicators (higher priority)
            if content:
                for doc_category, keywords in content_indicators.items():
                    matches = sum(1 for keyword in keywords if keyword in content)
                    if matches > confidence:
                        confidence = matches
                        doc_type = doc_category
            
            # File extension-specific defaults
            if confidence == 0:
                if file_extension == '.pdf':
                    if 'invoice' in clean_filename or 'bill' in clean_filename:
                        doc_type = "invoice"
                    elif 'contract' in clean_filename or 'agreement' in clean_filename:
                        doc_type = "contract"
                    elif 'report' in clean_filename:
                        doc_type = "report"
                    else:
                        doc_type = "PDF document"
                elif file_extension in {'.doc', '.docx'}:
                    doc_type = "Word document"
                elif file_extension in {'.xls', '.xlsx'}:
                    doc_type = "spreadsheet"
                elif file_extension in {'.ppt', '.pptx'}:
                    doc_type = "presentation"
                elif file_extension in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}:
                    doc_type = "image file"
                elif file_extension == '.txt':
                    doc_type = "text document"
                elif file_extension == '.md':
                    doc_type = "markdown document"
                elif file_extension == '.csv':
                    doc_type = "data file"
            
            return doc_type.title()
            
        except Exception as e:
            return "Document"

    def get_document_summary(self, file_path, max_sentences=3):
        """Generate a content summary of the document"""
        if self.openai_api_key:
            return [self.get_chatgpt_content_summary(file_path)]
        else:
            return [self.get_local_content_summary(file_path)]

    def create_pdf_summary(self, output_dir=None, summarize_only=False):
        """Create a comprehensive PDF summary of all documents"""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.colors import black, blue, darkblue
        except ImportError:
            print("Warning: reportlab library not available. Install with: pip install reportlab")
            print("Falling back to Markdown summary...")
            return self.create_summary_document(output_dir, summarize_only)
        
        if output_dir is None:
            output_dir = self.folder_path
        
        output_dir = Path(output_dir)
        timestamp = datetime.now().strftime("%Y.%m.%d")
        
        if summarize_only:
            pdf_filename = f"{timestamp}_Document_Analysis_Summary.pdf"
        else:
            pdf_filename = f"{timestamp}_Document_Processing_Summary.pdf"
        
        pdf_path = output_dir / pdf_filename
        
        # Ensure unique filename
        counter = 1
        while pdf_path.exists():
            if summarize_only:
                pdf_filename = f"{timestamp}_Document_Analysis_Summary_{counter}.pdf"
            else:
                pdf_filename = f"{timestamp}_Document_Processing_Summary_{counter}.pdf"
            pdf_path = output_dir / pdf_filename
            counter += 1
        
        # Create PDF document
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=darkblue,
            alignment=1  # Center
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=blue
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubheading',
            parent=styles['Heading3'],
            fontSize=12,
            spaceAfter=6,
            spaceBefore=12,
            textColor=black
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leftIndent=12
        )
        
        # Content list
        content = []
        
        # Title
        if summarize_only:
            title = "Document Analysis Summary"
        else:
            title = "Document Processing Summary"
        content.append(Paragraph(title, title_style))
        
        # Metadata
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        folder_name = str(self.folder_path.resolve())
        
        content.append(Spacer(1, 20))
        content.append(Paragraph(f"<b>Generated:</b> {current_time}", styles['Normal']))
        content.append(Paragraph(f"<b>Folder:</b> {folder_name}", styles['Normal']))
        
        # Get files to process
        if summarize_only:
            # For summary-only mode, process all files (not just unprocessed ones)
            all_files = []
            for file_path in self.folder_path.iterdir():
                if file_path.is_file() and not file_path.name.startswith('.'):
                    all_files.append(file_path)
            files_to_process = sorted(all_files, key=lambda x: x.name.lower())
        else:
            # For processing mode, use the usual logic
            files_to_process = [
                file_path for file_path in self.folder_path.iterdir()
                if self.is_valid_file(file_path)
            ]
        
        content.append(Paragraph(f"<b>Files Analyzed:</b> {len(files_to_process)}", styles['Normal']))
        content.append(Spacer(1, 30))
        
        # Document summaries
        if files_to_process:
            content.append(Paragraph("Document Analysis", heading_style))
            content.append(Spacer(1, 12))
            
            print(f"📊 Analyzing {len(files_to_process)} documents...")
            
            for i, file_path in enumerate(files_to_process, 1):
                print(f"   📄 Processing {i}/{len(files_to_process)}: {file_path.name}")
                
                # Extract clean title from filename
                filename = file_path.stem
                if re.match(r'^\d{4}\.\d{2}\.\d{2}_', filename):
                    clean_title = filename[11:].replace('_', ' ').replace('-', ' ').title()
                else:
                    clean_title = filename.replace('_', ' ').replace('-', ' ').title()
                
                # File details
                file_size = file_path.stat().st_size
                file_size_str = self.format_file_size(file_size)
                file_ext = file_path.suffix.upper()
                
                # Add document section - just title and summary
                content.append(Paragraph(f"{i}. {clean_title}", subheading_style))
                
                # Get document content summary
                try:
                    if self.openai_api_key:
                        print(f"      🤖 Generating content summary with ChatGPT...")
                        summary = self.get_chatgpt_content_summary(file_path)
                    else:
                        print(f"      � Analyzing document content...")
                        summary = self.get_local_content_summary(file_path)
                    
                    # Clean summary for PDF
                    clean_summary = summary.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
                    content.append(Paragraph(clean_summary, body_style))
                
                except Exception as e:
                    print(f"      ⚠️  Error generating summary: {str(e)}")
                    content.append(Paragraph(f"<b>Summary:</b> Error analyzing document content: {str(e)}", body_style))
                
                content.append(Spacer(1, 20))
                
                # Add page break every 3-4 documents to avoid crowding
                if i % 4 == 0 and i < len(files_to_process):
                    content.append(PageBreak())
        
        else:
            content.append(Paragraph("No documents found to analyze.", styles['Normal']))
        
        # Statistics section
        print(f"📈 Generating statistics and building PDF...")
        content.append(PageBreak())
        content.append(Paragraph("Summary Statistics", heading_style))
        content.append(Spacer(1, 12))
        
        # File type breakdown
        file_types = {}
        total_size = 0
        
        for file_path in files_to_process:
            ext = file_path.suffix.lower()
            if ext not in file_types:
                file_types[ext] = 0
            file_types[ext] += 1
            total_size += file_path.stat().st_size
        
        content.append(Paragraph(f"<b>Total Documents:</b> {len(files_to_process)}", styles['Normal']))
        content.append(Paragraph(f"<b>Total Size:</b> {self.format_file_size(total_size)}", styles['Normal']))
        content.append(Spacer(1, 12))
        
        if file_types:
            content.append(Paragraph("<b>File Types:</b>", styles['Normal']))
            for ext, count in sorted(file_types.items()):
                ext_display = ext.upper() if ext else "No extension"
                content.append(Paragraph(f"• {ext_display}: {count} files", body_style))
        
        # Build PDF
        print(f"📝 Finalizing PDF document...")
        doc.build(content)
        print(f"✅ PDF generation complete!")
        
        return pdf_path

    def print_summary(self):
        """Print a final summary of the operation"""
        print("=" * 80)
        print("OPERATION SUMMARY")
        print("=" * 80)
        print(f"Successfully processed: {len(self.processed_files)} files")
        print(f"Errors encountered: {len(self.errors)} files")
        print(f"Date extraction: {'Enabled' if self.use_file_dates else 'Disabled'}")
        
        if self.processed_files:
            print("\nProcessed files with extracted dates:")
            for old_name, new_name, extracted_date in self.processed_files:
                print(f"  {old_name} -> {new_name} [Date: {extracted_date.strftime('%Y-%m-%d')}]")
        
        if self.errors:
            print("\nFiles with errors:")
            for filename, error in self.errors:
                print(f"  - {filename}: {error}")
        
        # Create summary document
        summary_path = self.create_summary_document()
        if summary_path:
            print(f"\nDetailed summary document created: {summary_path.name}")


def main():
    parser = argparse.ArgumentParser(
        description="Rename documents with date prefix extracted from filenames, remove dates from filenames, or create comprehensive PDF summaries"
    )
    parser.add_argument(
        "folder",
        help="Path to the folder containing documents to rename"
    )
    parser.add_argument(
        "--date",
        help="Default date to use if none found in filename (YYYY-MM-DD format). Default: today's date"
    )
    parser.add_argument(
        "--no-extract",
        action="store_true",
        help="Don't extract dates from filenames, use default/override date for all files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually renaming files"
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Don't create a summary document"
    )
    parser.add_argument(
        "--remove-dates",
        action="store_true",
        help="Remove date patterns from end of filenames instead of adding date prefixes"
    )
    parser.add_argument(
        "--openai-api-key",
        help="OpenAI API key for ChatGPT-powered document summaries"
    )
    parser.add_argument(
        "--summarize-only",
        action="store_true",
        help="Create comprehensive PDF summary of all documents without renaming files (includes AI-powered summaries when --openai-api-key provided)"
    )
    
    args = parser.parse_args()
    
    try:
        use_file_dates = not args.no_extract
        create_summary = not args.no_summary
        
        renamer = DocumentRenamer(args.folder, args.date, use_file_dates, args.openai_api_key)
        
        if args.summarize_only:
            # Summary-only mode: create PDF summary without renaming
            print(f"Creating comprehensive PDF summary for folder: {args.folder}")
            print("=" * 70)
            
            pdf_path = renamer.create_pdf_summary(summarize_only=True)
            print(f"\n✅ PDF summary created: {pdf_path.name}")
            print(f"Location: {pdf_path.resolve()}")
            
        elif args.remove_dates:
            # Remove dates from filenames
            renamer.remove_dates_from_folder(dry_run=args.dry_run)
        else:
            # Normal operation: add date prefixes
            renamer.process_folder(dry_run=args.dry_run, create_summary=create_summary)
            
            if not args.dry_run:
                renamer.print_summary()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()