#!/usr/bin/env python3
"""
Document Renamer - Renames documents with date prefix and provides summaries
"""

import os
import sys
import re
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
    
    def get_chatgpt_summary(self, file_path, max_sentences=3):
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

    def get_document_summary(self, file_path, max_sentences=3):
        """Generate a 3-sentence summary of the document"""
        if self.openai_api_key:
            return self.get_chatgpt_summary(file_path, max_sentences)
        else:
            return self.get_fallback_summary(file_path, max_sentences)

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
        description="Rename documents with date prefix extracted from filenames, or remove dates from filenames"
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
    
    args = parser.parse_args()
    
    try:
        use_file_dates = not args.no_extract
        create_summary = not args.no_summary
        
        renamer = DocumentRenamer(args.folder, args.date, use_file_dates, args.openai_api_key)
        
        if args.remove_dates:
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