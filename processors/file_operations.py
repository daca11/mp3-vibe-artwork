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
from processors.musicbrainz_client import MusicBrainzClient

# Set up logging
logger = logging.getLogger(__name__)

class FileOperations:
    """
    Handles file operations including output folder management, 
    MP3 copying with artwork embedding, and filename parsing.
    """
    
    def __init__(self, output_base_dir: Union[str, Path] = "output", enable_musicbrainz: bool = True):
        """
        Initialize file operations.
        
        Args:
            output_base_dir: Base directory for output files
            enable_musicbrainz: Whether to enable MusicBrainz artwork discovery
        """
        self.output_base_dir = Path(output_base_dir)
        self.mp3_handler = MP3FileHandler()
        self.artwork_processor = ArtworkProcessor()
        
        # Initialize MusicBrainz client if enabled
        self.enable_musicbrainz = enable_musicbrainz
        self.musicbrainz_client = None
        if enable_musicbrainz:
            try:
                self.musicbrainz_client = MusicBrainzClient()
                logger.info("MusicBrainz integration enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize MusicBrainz client: {e}")
                self.enable_musicbrainz = False
    
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
    
    def generate_unique_filename(self, output_dir: Path, base_filename: str) -> Path:
        """
        Generate a unique filename to avoid conflicts.
        
        Args:
            output_dir: Output directory path
            base_filename: Base filename (e.g., "song.mp3")
            
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
            new_name = f"{stem}_{counter:03d}{suffix}"
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
                            artwork_mime: str = "image/jpeg") -> Dict[str, Union[bool, str, Path]]:
        """
        Copy MP3 file to output directory with optional artwork embedding.
        
        Args:
            source_path: Source MP3 file path
            output_dir: Output directory
            artwork_data: Optional artwork data to embed
            artwork_mime: MIME type of artwork
            
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
            
            # Generate unique output filename
            output_path = self.generate_unique_filename(output_dir, source_path.name)
            
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
        
        # Remove track numbers at the beginning
        cleaned = re.sub(r'^\d+\.?\s*', '', cleaned)
        
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
            
            # Step 3: Extract metadata (continue even if MP3 is invalid for filename parsing)
            result['processing_steps'].append("Extracting metadata")
            result['metadata'] = self.mp3_handler.extract_metadata(source_path)
            
            # Step 4: Parse filename if metadata is missing
            if not result['metadata']['artist'] or not result['metadata']['title']:
                result['processing_steps'].append("Parsing filename for missing metadata")
                result['parsing_info'] = self.parse_filename_for_metadata(source_path.name)
            
            # If MP3 is invalid but we have filename info, continue with artwork processing only
            if not result['file_info']['is_valid']:
                # Check if we have enough info from filename to attempt artwork search
                parsed_info = result.get('parsing_info', {})
                if parsed_info and parsed_info.get('artist') and process_artwork:
                    logger.info("MP3 invalid but attempting artwork search from filename")
                    result['processing_steps'].append("Attempting artwork search despite invalid MP3")
                    
                    # Try MusicBrainz search with parsed filename info
                    if self.enable_musicbrainz:
                        result['processing_steps'].append("Searching MusicBrainz for artwork")
                        online_artwork = self.search_artwork_online(result['metadata'], parsed_info)
                        
                        if online_artwork:
                            downloaded_data, downloaded_mime = online_artwork
                            # Save artwork as separate file since we can't embed in invalid MP3
                            artwork_filename = source_path.stem + "_artwork" + (".jpg" if downloaded_mime == "image/jpeg" else ".png")
                            artwork_path = source_path.parent / artwork_filename
                            
                            try:
                                artwork_path.write_bytes(downloaded_data)
                                result['artwork_info'] = {
                                    'had_original': False,
                                    'was_compliant': False,
                                    'processing_needed': False,
                                    'processing_successful': True,
                                    'musicbrainz_searched': True,
                                    'musicbrainz_found': True,
                                    'artwork_saved_separately': str(artwork_path)
                                }
                                logger.info(f"Saved artwork separately as: {artwork_path}")
                            except Exception as e:
                                logger.error(f"Failed to save artwork: {e}")
                
                result['error'] = result['file_info']['error']
                return result
            
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
                        'processing_successful': artwork_result['is_compliant'],
                        'musicbrainz_searched': False,
                        'musicbrainz_found': False
                    }
                    
                    if artwork_result['is_compliant'] and artwork_result['processed_data']:
                        artwork_data = artwork_result['processed_data']
                        artwork_mime = "image/jpeg"  # Processor typically outputs JPEG
                
                else:
                    result['artwork_info'] = {
                        'had_original': False,
                        'was_compliant': False,
                        'processing_needed': False,
                        'processing_successful': False,
                        'musicbrainz_searched': False,
                        'musicbrainz_found': False
                    }
                
                # If no valid artwork found, try MusicBrainz search
                if not artwork_data and self.enable_musicbrainz:
                    result['processing_steps'].append("Searching MusicBrainz for artwork")
                    result['artwork_info']['musicbrainz_searched'] = True
                    
                    online_artwork = self.search_artwork_online(
                        result['metadata'], 
                        result.get('parsing_info')
                    )
                    
                    if online_artwork:
                        downloaded_data, downloaded_mime = online_artwork
                        
                        # Process downloaded artwork to ensure compliance
                        artwork_result = self.artwork_processor.process_artwork(
                            downloaded_data,
                            force_compliance=True
                        )
                        
                        if artwork_result['is_compliant'] and artwork_result['processed_data']:
                            artwork_data = artwork_result['processed_data']
                            artwork_mime = "image/jpeg"
                            result['artwork_info']['musicbrainz_found'] = True
                            result['artwork_info']['processing_successful'] = True
                            logger.info("Successfully found and processed artwork from MusicBrainz")
                        else:
                            logger.warning("Downloaded artwork from MusicBrainz could not be processed to compliance")
                    else:
                        logger.info("No suitable artwork found on MusicBrainz")
            
            # Step 6: Create output directory
            if output_dir is None:
                output_dir = self.create_output_folder()
            else:
                self.create_output_folder(str(output_dir.name) if output_dir.name != self.output_base_dir.name else None)
            
            result['processing_steps'].append(f"Created output directory: {output_dir}")
            
            # Step 7: Copy file with artwork
            result['processing_steps'].append("Copying file with processed artwork")
            copy_result = self.copy_mp3_with_artwork(
                source_path, output_dir, artwork_data, artwork_mime
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

    def process_mp3_file_with_choice(self, source_path: Path, output_dir: Optional[Path] = None,
                                   user_artwork_choice: Optional[Dict] = None) -> Dict[str, Union[bool, str, Path, Dict]]:
        """
        Process MP3 file with user-selected artwork choice.
        
        Args:
            source_path: Source MP3 file path
            output_dir: Output directory (creates default if None)
            user_artwork_choice: User's artwork selection with 'artwork_url' or 'skip_artwork'
            
        Returns:
            Dictionary with comprehensive processing results
        """
        # Start with normal processing
        result = self.process_mp3_file(source_path, output_dir, process_artwork=False)
        
        # If basic processing failed, return early
        if not result['success']:
            return result
        
        # Handle user artwork choice
        if user_artwork_choice and not user_artwork_choice.get('skip_artwork', False):
            artwork_url = user_artwork_choice.get('artwork_url')
            
            if artwork_url and self.enable_musicbrainz and self.musicbrainz_client:
                try:
                    result['processing_steps'].append("Downloading user-selected artwork")
                    
                    # Download the selected artwork
                    artwork_data = self.musicbrainz_client.download_artwork(artwork_url)
                    
                    if artwork_data:
                        # Process artwork to ensure compliance
                        artwork_result = self.artwork_processor.process_artwork(
                            artwork_data,
                            force_compliance=True
                        )
                        
                        if artwork_result['is_compliant'] and artwork_result['processed_data']:
                            # Embed the processed artwork
                            output_path = result['output_path']
                            success = self.embed_artwork_in_mp3(
                                output_path, 
                                artwork_result['processed_data'],
                                "image/jpeg"
                            )
                            
                            if success:
                                result['artwork_info'] = {
                                    'had_original': result.get('artwork_info', {}).get('had_original', False),
                                    'was_compliant': False,
                                    'processing_needed': True,
                                    'processing_successful': True,
                                    'musicbrainz_searched': True,
                                    'musicbrainz_found': True,
                                    'user_selected': True,
                                    'selected_url': artwork_url
                                }
                                result['processing_steps'].append("User-selected artwork embedded successfully")
                                logger.info(f"Successfully embedded user-selected artwork from: {artwork_url}")
                            else:
                                logger.warning(f"Failed to embed user-selected artwork in: {output_path}")
                        else:
                            logger.warning(f"User-selected artwork could not be processed to compliance")
                    else:
                        logger.warning(f"Failed to download user-selected artwork from: {artwork_url}")
                        
                except Exception as e:
                    logger.error(f"Error processing user-selected artwork: {e}")
        
        elif user_artwork_choice and user_artwork_choice.get('skip_artwork', False):
            # User chose to skip artwork
            result['artwork_info'] = {
                'had_original': result.get('artwork_info', {}).get('had_original', False),
                'was_compliant': False,
                'processing_needed': False,
                'processing_successful': False,
                'musicbrainz_searched': False,
                'musicbrainz_found': False,
                'user_skipped': True
            }
            result['processing_steps'].append("User chose to skip artwork processing")
            logger.info("User chose to skip artwork for this file")
        
        return result
    
    def search_artwork_online(self, metadata: Dict, parsed_info: Dict = None, return_options: bool = False) -> Union[Optional[Tuple[bytes, str]], List[Dict]]:
        """
        Search for artwork online using MusicBrainz.
        
        Args:
            metadata: Extracted MP3 metadata
            parsed_info: Parsed filename information (fallback)
            return_options: If True, returns list of artwork options instead of downloading
            
        Returns:
            If return_options=False: Tuple of (artwork_data, mime_type) or None if not found
            If return_options=True: List of artwork option dictionaries
        """
        if not self.enable_musicbrainz or not self.musicbrainz_client:
            logger.debug("MusicBrainz search disabled or client unavailable")
            return [] if return_options else None
        
        try:
            # Extract search parameters from metadata (handle None metadata)
            if metadata is None:
                metadata = {}
            
            artist = metadata.get('artist', '') or ''
            album = metadata.get('album', '') or ''
            title = metadata.get('title', '') or ''
            
            # Ensure we have strings, not None
            artist = artist.strip() if artist else ''
            album = album.strip() if album else ''
            title = title.strip() if title else ''
            
            # Use parsed filename info as fallback
            if not artist and parsed_info:
                parsed_artist = parsed_info.get('artist', '') or ''
                artist = parsed_artist.strip() if parsed_artist else ''
            if not title and parsed_info:
                parsed_title = parsed_info.get('title', '') or ''
                title = parsed_title.strip() if parsed_title else ''
            
            if not artist:
                logger.debug("No artist information available for MusicBrainz search")
                logger.debug(f"Metadata: {metadata}")
                logger.debug(f"Parsed info: {parsed_info}")
                return [] if return_options else None
            
            logger.info(f"Searching MusicBrainz for artwork: {artist} - {album or title or 'Unknown'}")
            logger.debug(f"Search parameters - Artist: '{artist}', Album: '{album}', Title: '{title}'")
            
            # Search for releases
            releases = self.musicbrainz_client.search_and_get_artwork(
                artist=artist,
                album=album if album else None,
                title=title if title else None
            )
            
            logger.debug(f"MusicBrainz search returned {len(releases) if releases else 0} releases")
            
            if not releases:
                logger.info("No releases found in MusicBrainz search")
                return [] if return_options else None
            
            # Collect all artwork options
            artwork_options = []
            
            for release in releases[:5]:  # Limit to top 5 releases
                artwork_urls = release.get('artwork_urls', [])
                
                if not artwork_urls:
                    logger.debug(f"No artwork URLs for release: {release['title']}")
                    continue
                
                # Process each artwork option
                for artwork in artwork_urls[:3]:  # Max 3 artworks per release
                    option = {
                        'release_id': release['id'],
                        'release_title': release['title'],
                        'release_artist': release['artist'],
                        'release_date': release.get('date', ''),
                        'artwork_url': artwork.get('image_url', ''),
                        'thumbnail_url': artwork.get('thumbnail_url', ''),
                        'is_front': artwork.get('is_front', False),
                        'types': artwork.get('types', []),
                        'width': artwork.get('width'),
                        'height': artwork.get('height'),
                        'comment': artwork.get('comment', ''),
                        'approved': artwork.get('approved', False)
                    }
                    artwork_options.append(option)
            
            # Sort options by preference (front covers first, approved first, larger images)
            artwork_options.sort(key=lambda x: (
                0 if x['is_front'] else 1,
                0 if x['approved'] else 1,
                -(x['width'] or 0)
            ))
            
            logger.info(f"Found {len(artwork_options)} artwork options")
            
            if return_options:
                return artwork_options
            
            # Legacy behavior: download the first/best option
            if artwork_options:
                best_option = artwork_options[0]
                url = best_option['thumbnail_url'] or best_option['artwork_url']
                if url:
                    logger.info(f"Downloading artwork from: {url}")
                    artwork_data = self.musicbrainz_client.download_artwork(url)
                    
                    if artwork_data:
                        # Determine MIME type from URL or use JPEG as default
                        mime_type = "image/jpeg"
                        if url.lower().endswith('.png'):
                            mime_type = "image/png"
                        
                        logger.info(f"Successfully downloaded artwork: {len(artwork_data)} bytes")
                        return (artwork_data, mime_type)
            
            logger.info("No suitable artwork found in MusicBrainz results")
            return [] if return_options else None
            
        except Exception as e:
            logger.error(f"Error during MusicBrainz artwork search: {e}")
            return [] if return_options else None 