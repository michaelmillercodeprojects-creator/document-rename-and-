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


class DocumentRenamer:
    def __init__(self, folder_path, date_override=None, use_file_dates=True):
        """
        Initialize the DocumentRenamer
        
        Args:
            folder_path (str): Path to the folder containing documents to rename
            date_override (str): Optional date override in YYYY-MM-DD format
            use_file_dates (bool): If True, extract dates from document content
        """
        self.folder_path = Path(folder_path)
        self.use_file_dates = use_file_dates
        
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
    
    def get_document_summary(self, file_path, max_sentences=3):
        """Generate a 3-sentence summary of the document content"""
        try:
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                        
                        # Clean up the content
                        content = content.strip()
                        
                        # Remove common document formatting
                        lines = content.split('\n')
                        cleaned_lines = []
                        
                        for line in lines:
                            line = line.strip()
                            # Skip empty lines, headers with #, and very short lines
                            if len(line) > 10 and not line.startswith('#') and not line.startswith('*'):
                                # Skip lines that look like metadata
                                if not any(keyword in line.lower() for keyword in ['date:', 'time:', 'location:', 'attendees:', 'customer:', 'invoice']):
                                    cleaned_lines.append(line)
                        
                        # Join the cleaned content
                        cleaned_content = ' '.join(cleaned_lines)
                        
                        # Split into sentences
                        sentences = []
                        for delimiter in ['. ', '! ', '? ']:
                            parts = cleaned_content.split(delimiter)
                            if len(parts) > 1:
                                for i, part in enumerate(parts[:-1]):
                                    sentences.append(part.strip() + delimiter.strip())
                                sentences.append(parts[-1].strip())
                                break
                        else:
                            # If no sentence delimiters found, split by length
                            words = cleaned_content.split()
                            chunk_size = len(words) // max_sentences if len(words) > max_sentences * 10 else len(words)
                            for i in range(0, len(words), chunk_size):
                                chunk = ' '.join(words[i:i + chunk_size])
                                if chunk.strip():
                                    sentences.append(chunk.strip())
                        
                        # Filter and select the best sentences
                        good_sentences = []
                        for sentence in sentences:
                            sentence = sentence.strip()
                            if len(sentence) > 20 and len(sentence) < 200:  # Reasonable sentence length
                                good_sentences.append(sentence)
                        
                        # Take the first few good sentences, up to max_sentences
                        summary_sentences = good_sentences[:max_sentences]
                        
                        # If we don't have enough good sentences, create a descriptive summary
                        if len(summary_sentences) < 2:
                            # Analyze the document type and content
                            content_lower = content.lower()
                            
                            if 'invoice' in content_lower:
                                summary_sentences = [
                                    f"This is an invoice document for business services or products.",
                                    f"It contains billing information, itemized charges, and payment terms.",
                                    f"The document includes customer details and financial calculations."
                                ]
                            elif 'meeting' in content_lower or 'minutes' in content_lower:
                                summary_sentences = [
                                    f"This document contains meeting minutes or notes from a business meeting.",
                                    f"It includes attendee information, agenda items, and discussion points.",
                                    f"Action items and follow-up tasks are documented for future reference."
                                ]
                            elif 'report' in content_lower or 'financial' in content_lower:
                                summary_sentences = [
                                    f"This is a business report containing performance or financial data.",
                                    f"It includes analysis, metrics, and key performance indicators.",
                                    f"The report provides insights and recommendations for business decisions."
                                ]
                            elif 'project' in content_lower:
                                summary_sentences = [
                                    f"This document relates to project management and planning activities.",
                                    f"It contains project status updates, timelines, and deliverables.",
                                    f"Team information and project milestones are documented."
                                ]
                            else:
                                # Generic summary based on content
                                word_count = len(content.split())
                                doc_type = file_path.suffix.upper().replace('.', '')
                                summary_sentences = [
                                    f"This is a {doc_type} document containing {word_count} words of text content.",
                                    f"The document appears to contain business or organizational information.",
                                    f"It includes structured information relevant to its intended purpose."
                                ]
                        
                        return summary_sentences[:max_sentences]
                        
                except UnicodeDecodeError:
                    continue
            
            return ["Unable to read document content.", "The file may be in an unsupported format.", "No content summary available."]
            
        except Exception as e:
            return [f"Error analyzing document: {str(e)}", "Unable to generate content summary.", "Manual review may be required."]

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
        description="Rename documents with date prefix extracted from document content"
    )
    parser.add_argument(
        "folder",
        help="Path to the folder containing documents to rename"
    )
    parser.add_argument(
        "--date",
        help="Default date to use if none found in document (YYYY-MM-DD format). Default: today's date"
    )
    parser.add_argument(
        "--no-extract",
        action="store_true",
        help="Don't extract dates from document content, use default/override date for all files"
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
    
    args = parser.parse_args()
    
    try:
        use_file_dates = not args.no_extract
        create_summary = not args.no_summary
        
        renamer = DocumentRenamer(args.folder, args.date, use_file_dates)
        renamer.process_folder(dry_run=args.dry_run, create_summary=create_summary)
        
        if not args.dry_run:
            renamer.print_summary()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()