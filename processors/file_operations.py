#!/usr/bin/env python3
"""
File Operations Module
Handles output folder management, MP3 file copying with artwork embedding, and filename parsing.
"""

import os
import re
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, ID3NoHeaderError
from processors.file_handler import MP3FileHandler
from processors.artwork_processor import ArtworkProcessor

# Set up logging
logger = logging.getLogger(__name__)

class FileOperations:
    """
    Handles file operations including output folder management, 
    MP3 copying with artwork embedding, and filename parsing.
    """
    
    def __init__(self, output_base_dir: Union[str, Path] = "output"):
        """
        Initialize file operations.
        
        Args:
            output_base_dir: Base directory for output files
        """
        self.output_base_dir = Path(output_base_dir)
        self.mp3_handler = MP3FileHandler()
        self.artwork_processor = ArtworkProcessor()
    
    def create_output_folder(self, subfolder: Optional[str] = None) -> Path:
        """
        Create output folder with proper permissions.
        
        Args:
            subfolder: Optional subfolder name for organization
            
        Returns:
            Path to the created output folder
            
        Raises:
            PermissionError: If unable to create folder or write to it
            OSError: If folder creation fails
        """
        if subfolder:
            output_path = self.output_base_dir / subfolder
        else:
            output_path = self.output_base_dir
        
        try:
            # Create directory if it doesn't exist
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions
            test_file = output_path / ".write_test"
            test_file.touch()
            test_file.unlink()
            
            logger.info(f"Output folder ready: {output_path}")
            return output_path
            
        except PermissionError as e:
            logger.error(f"Permission denied creating output folder: {output_path}")
            raise PermissionError(f"Cannot create or write to output folder: {output_path}") from e
        except OSError as e:
            logger.error(f"OS error creating output folder: {output_path} - {e}")
            raise OSError(f"Failed to create output folder: {output_path}") from e
    
    def generate_output_filename(self, artist: str, title: str) -> str:
        """
        Generate output filename using Artist - Title.mp3 convention.
        
        Args:
            artist: Artist name
            title: Song title
            
        Returns:
            Filename in "Artist - Title.mp3" format
        """
        # Use fallbacks for missing values
        clean_artist = self._sanitize_for_filename(artist) if artist else "Unknown Artist"
        clean_title = self._sanitize_for_filename(title) if title else "Unknown Title"
        
        return f"{clean_artist} - {clean_title}.mp3"
    
    def _sanitize_for_filename(self, text: str) -> str:
        """
        Sanitize text for use in filenames while preserving readability.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text safe for filenames
        """
        if not text:
            return ""
        
        # Remove or replace characters that are problematic for filenames
        # Keep: letters, numbers, spaces, hyphens, parentheses, brackets, ampersands
        import re
        
        # Replace problematic characters but keep readability
        sanitized = text.strip()
        
        # Remove leading/trailing quotes
        sanitized = sanitized.strip('\'"')
        
        # Replace file system reserved characters with safe alternatives
        replacements = {
            '/': '-',
            '\\': '-',
            ':': '-',
            '*': '',
            '?': '',
            '"': "'",
            '<': '(',
            '>': ')',
            '|': '-'
        }
        
        for old, new in replacements.items():
            sanitized = sanitized.replace(old, new)
        
        # Remove any remaining problematic characters while preserving spaces and common punctuation
        sanitized = re.sub(r'[^\w\s\-\(\)\[\]&\'".!,]', '', sanitized)
        
        # Clean up multiple spaces
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized

    def generate_unique_filename(self, output_dir: Path, base_filename: str) -> Path:
        """
        Generate a unique filename to avoid conflicts.
        
        Args:
            output_dir: Output directory path
            base_filename: Base filename (e.g., "Artist - Title.mp3")
            
        Returns:
            Unique file path
        """
        base_path = output_dir / base_filename
        
        if not base_path.exists():
            return base_path
        
        # Extract name and extension
        stem = base_path.stem
        suffix = base_path.suffix
        
        # Generate unique filename with counter
        counter = 1
        while True:
            new_name = f"{stem} ({counter}){suffix}"
            new_path = output_dir / new_name
            
            if not new_path.exists():
                logger.debug(f"Generated unique filename: {new_name}")
                return new_path
            
            counter += 1
            
            # Safety check to prevent infinite loop
            if counter > 9999:
                raise ValueError(f"Unable to generate unique filename for {base_filename}")
    
    def embed_artwork_in_mp3(self, mp3_file_path: Path, artwork_data: bytes, 
                           mime_type: str = "image/jpeg") -> bool:
        """
        Embed artwork into an MP3 file's ID3 tags.
        
        Args:
            mp3_file_path: Path to the MP3 file
            artwork_data: Image data bytes
            mime_type: MIME type of the image (image/jpeg or image/png)
            
        Returns:
            True if embedding was successful, False otherwise
        """
        try:
            # Load the MP3 file
            audio_file = MP3(str(mp3_file_path))
            
            # Ensure ID3 tags exist
            if audio_file.tags is None:
                audio_file.add_tags()
            
            # Remove existing APIC frames
            audio_file.tags.delall('APIC')
            
            # Create new APIC frame
            apic = APIC(
                encoding=3,  # UTF-8
                mime=mime_type,
                type=3,  # Front cover
                desc='Cover',
                data=artwork_data
            )
            
            # Add the artwork
            audio_file.tags.add(apic)
            
            # Save the changes
            audio_file.save()
            
            logger.info(f"Successfully embedded artwork in {mp3_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to embed artwork in {mp3_file_path}: {e}")
            return False
    
    def copy_mp3_with_artwork(self, source_path: Path, output_dir: Path, 
                            artwork_data: Optional[bytes] = None,
                            artwork_mime: str = "image/jpeg",
                            output_filename: Optional[str] = None) -> Dict[str, Union[bool, str, Path]]:
        """
        Copy MP3 file to output directory with optional artwork embedding.
        
        Args:
            source_path: Source MP3 file path
            output_dir: Output directory
            artwork_data: Optional artwork data to embed
            artwork_mime: MIME type of artwork
            output_filename: Optional custom output filename
            
        Returns:
            Dictionary with operation results:
            {
                'success': bool,
                'output_path': Path or None,
                'error': str or None,
                'artwork_embedded': bool,
                'metadata_preserved': bool
            }
        """
        result = {
            'success': False,
            'output_path': None,
            'error': None,
            'artwork_embedded': False,
            'metadata_preserved': False
        }
        
        try:
            # Validate source file
            if not source_path.exists():
                result['error'] = f"Source file does not exist: {source_path}"
                return result
            
            is_valid, validation_error = self.mp3_handler.validate_mp3_file(source_path)
            if not is_valid:
                result['error'] = f"Invalid MP3 file: {validation_error}"
                return result
            
            # Use provided filename or fallback to original
            filename_to_use = output_filename or source_path.name
            output_path = self.generate_unique_filename(output_dir, filename_to_use)
            
            # Copy the file
            shutil.copy2(source_path, output_path)
            logger.info(f"Copied MP3 file: {source_path} -> {output_path}")
            
            result['output_path'] = output_path
            result['metadata_preserved'] = True
            
            # Embed artwork if provided
            if artwork_data:
                artwork_success = self.embed_artwork_in_mp3(output_path, artwork_data, artwork_mime)
                result['artwork_embedded'] = artwork_success
                
                if not artwork_success:
                    logger.warning(f"Artwork embedding failed for {output_path}")
            
            result['success'] = True
            logger.info(f"MP3 file operation completed successfully: {output_path}")
            
        except Exception as e:
            error_msg = f"Error copying MP3 file {source_path}: {e}"
            logger.error(error_msg)
            result['error'] = error_msg
            
            # Cleanup on failure
            if result['output_path'] and result['output_path'].exists():
                try:
                    result['output_path'].unlink()
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup after error: {cleanup_error}")
        
        return result
    
    def parse_filename_for_metadata(self, filename: str) -> Dict[str, Optional[str]]:
        """
        Parse filename to extract artist and title metadata.
        
        Args:
            filename: MP3 filename (with or without extension)
            
        Returns:
            Dictionary with parsed metadata:
            {
                'artist': str or None,
                'title': str or None,
                'original_filename': str,
                'parsing_method': str or None
            }
        """
        result = {
            'artist': None,
            'title': None,
            'original_filename': filename,
            'parsing_method': None
        }
        
        # Remove file extension
        base_name = Path(filename).stem
        
        # Clean up common filename artifacts
        cleaned_name = self._clean_filename(base_name)
        
        if not cleaned_name:
            return result
        
        # Try different parsing patterns
        patterns = [
            # Artist - Title
            (r'^(.+?)\s*[-–—]\s*(.+)$', 'hyphen_separator'),
            # Artist | Title
            (r'^(.+?)\s*\|\s*(.+)$', 'pipe_separator'),
            # Artist _ Title
            (r'^(.+?)_+(.+)$', 'underscore_separator'),
            # Artist Title (space separation, requires common patterns)
            (r'^(.+?)\s+(feat\.|ft\.|featuring)\s+(.+)$', 'featuring_pattern'),
        ]
        
        for pattern, method in patterns:
            match = re.match(pattern, cleaned_name, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                if method == 'featuring_pattern':
                    # Special handling for featuring patterns
                    result['artist'] = self._clean_parsed_text(groups[0])
                    result['title'] = self._clean_parsed_text(f"{groups[1]} {groups[2]}")
                else:
                    result['artist'] = self._clean_parsed_text(groups[0])
                    result['title'] = self._clean_parsed_text(groups[1])
                
                result['parsing_method'] = method
                break
        
        # Log parsing result
        if result['artist'] and result['title']:
            logger.debug(f"Parsed filename '{filename}' -> Artist: '{result['artist']}', Title: '{result['title']}' (method: {result['parsing_method']})")
        else:
            logger.debug(f"Could not parse filename '{filename}' for metadata")
        
        return result
    
    def _clean_filename(self, filename: str) -> str:
        """
        Clean filename by removing common artifacts.
        
        Args:
            filename: Raw filename
            
        Returns:
            Cleaned filename
        """
        if not filename:
            return ""
        
        # Remove common prefixes/suffixes
        cleaned = filename
        
        # Remove track numbers at the beginning (formats: "01. ", "02-", "1 ")
        cleaned = re.sub(r'^\d+[\.\-\s]+', '', cleaned)
        
        # Remove quality indicators
        quality_patterns = [
            r'\[?\d+kbps\]?',
            r'\[?320\]?',
            r'\[?mp3\]?',
            r'\[?flac\]?',
            r'\b(320|256|192|128)k?\b',
        ]
        
        for pattern in quality_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Remove brackets and their contents (but keep the content if it looks like title/artist)
        # Only remove if it looks like technical info
        bracket_patterns = [
            r'\[[^\]]*\d+[^\]]*\]',  # Brackets with numbers (likely technical)
            r'\([^)]*\d+[^)]*\)',    # Parentheses with numbers
        ]
        
        for pattern in bracket_patterns:
            cleaned = re.sub(pattern, '', cleaned)
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _clean_parsed_text(self, text: str) -> str:
        """
        Clean parsed artist/title text.
        
        Args:
            text: Raw parsed text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        cleaned = text.strip()
        
        # Remove underscores and replace with spaces
        cleaned = cleaned.replace('_', ' ')
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Capitalize properly (title case)
        if cleaned:
            cleaned = cleaned.title()
        
        return cleaned
    
    def process_mp3_file(self, source_path: Path, output_dir: Optional[Path] = None,
                        process_artwork: bool = True) -> Dict[str, Union[bool, str, Path, Dict]]:
        """
        Complete MP3 file processing pipeline.
        
        Args:
            source_path: Source MP3 file path
            output_dir: Output directory (creates default if None)
            process_artwork: Whether to process artwork
            
        Returns:
            Dictionary with comprehensive processing results
        """
        result = {
            'success': False,
            'source_path': source_path,
            'output_path': None,
            'error': None,
            'file_info': {},
            'metadata': {},
            'artwork_info': {},
            'parsing_info': {},
            'processing_steps': []
        }
        
        try:
            # Step 1: Validate input
            result['processing_steps'].append("Validating input file")
            
            if not source_path.exists():
                result['error'] = f"Source file does not exist: {source_path}"
                return result
            
            # Step 2: Get file info
            result['processing_steps'].append("Extracting file information")
            result['file_info'] = self.mp3_handler.get_file_info(source_path)
            
            if not result['file_info']['is_valid']:
                result['error'] = result['file_info']['error']
                return result
            
            # Step 3: Extract metadata
            result['processing_steps'].append("Extracting metadata")
            result['metadata'] = self.mp3_handler.extract_metadata(source_path)
            
            # Step 4: Parse filename if metadata is missing
            if not result['metadata']['artist'] or not result['metadata']['title']:
                result['processing_steps'].append("Parsing filename for missing metadata")
                result['parsing_info'] = self.parse_filename_for_metadata(source_path.name)
            
            # Step 5: Handle artwork
            artwork_data = None
            artwork_mime = "image/jpeg"
            
            if process_artwork:
                result['processing_steps'].append("Processing artwork")
                
                # Extract existing artwork
                existing_artwork = self.mp3_handler.extract_artwork(source_path)
                
                if existing_artwork:
                    # Process existing artwork
                    artwork_result = self.artwork_processor.process_artwork(
                        existing_artwork['data'], 
                        force_compliance=True
                    )
                    
                    result['artwork_info'] = {
                        'had_original': True,
                        'was_compliant': artwork_result['is_compliant'] and not artwork_result['needs_processing'],
                        'processing_needed': artwork_result['needs_processing'],
                        'processing_successful': artwork_result['is_compliant']
                    }
                    
                    if artwork_result['is_compliant'] and artwork_result['processed_data']:
                        artwork_data = artwork_result['processed_data']
                        artwork_mime = "image/jpeg"  # Processor typically outputs JPEG
                
                else:
                    result['artwork_info'] = {
                        'had_original': False,
                        'was_compliant': False,
                        'processing_needed': False,
                        'processing_successful': False
                    }
            
            # Step 6: Create output directory
            if output_dir is None:
                output_dir = self.create_output_folder()
            else:
                self.create_output_folder(str(output_dir.name) if output_dir.name != self.output_base_dir.name else None)
            
            result['processing_steps'].append(f"Created output directory: {output_dir}")
            
            # Step 7: Generate proper output filename
            result['processing_steps'].append("Generating output filename")
            
            # Determine artist and title for filename
            artist = result['metadata'].get('artist') or result['parsing_info'].get('artist') or "Unknown Artist"
            title = result['metadata'].get('title') or result['parsing_info'].get('title') or "Unknown Title"
            
            # Generate proper filename using Artist - Title convention
            output_filename = self.generate_output_filename(artist, title)
            result['output_filename'] = output_filename
            
            # Step 8: Copy file with artwork
            result['processing_steps'].append("Copying file with processed artwork")
            copy_result = self.copy_mp3_with_artwork(
                source_path, output_dir, artwork_data, artwork_mime, output_filename
            )
            
            if copy_result['success']:
                result['output_path'] = copy_result['output_path']
                result['success'] = True
                result['processing_steps'].append("Processing completed successfully")
            else:
                result['error'] = copy_result['error']
            
        except Exception as e:
            error_msg = f"Error in MP3 processing pipeline: {e}"
            logger.error(error_msg)
            result['error'] = error_msg
        
        return result 