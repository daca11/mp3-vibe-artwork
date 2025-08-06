#!/usr/bin/env python3
"""
MP3 File Handler Module
Handles MP3 file detection, validation, ID3 metadata extraction, and artwork extraction.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, Tuple
from mutagen import File, MutagenError
from mutagen.mp3 import MP3
from mutagen.id3 import ID3NoHeaderError, APIC

# Set up logging
logger = logging.getLogger(__name__)

class MP3FileHandler:
    """
    Handles MP3 file operations including detection, validation, 
    metadata extraction, and artwork extraction.
    """
    
    # Supported MP3 file extensions (case insensitive)
    MP3_EXTENSIONS = {'.mp3', '.MP3', '.Mp3', '.mP3'}
    
    def __init__(self):
        """Initialize the MP3 file handler."""
        pass
    
    def detect_mp3_files(self, path: Union[str, Path]) -> List[Path]:
        """
        Detect MP3 files in a given directory or return single file if path is a file.
        
        Args:
            path: Directory path or single file path
            
        Returns:
            List of Path objects for detected MP3 files
            
        Raises:
            FileNotFoundError: If path doesn't exist
            PermissionError: If path is not accessible
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        
        if not os.access(path, os.R_OK):
            raise PermissionError(f"Path is not readable: {path}")
        
        mp3_files = []
        
        if path.is_file():
            # Single file case
            if self.is_mp3_file(path):
                mp3_files.append(path)
            else:
                logger.warning(f"File is not an MP3: {path}")
        elif path.is_dir():
            # Directory case - scan only current directory, no recursion
            try:
                for file_path in path.iterdir():
                    if file_path.is_file() and self.is_mp3_file(file_path):
                        mp3_files.append(file_path)
            except PermissionError as e:
                logger.error(f"Permission denied accessing directory: {path}")
                raise
        
        logger.info(f"Found {len(mp3_files)} MP3 files in {path}")
        return sorted(mp3_files)
    
    def is_mp3_file(self, file_path: Union[str, Path]) -> bool:
        """
        Check if a file is an MP3 based on extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file has MP3 extension, False otherwise
        """
        file_path = Path(file_path)
        return file_path.suffix in self.MP3_EXTENSIONS
    
    def validate_mp3_file(self, file_path: Union[str, Path]) -> Tuple[bool, Optional[str]]:
        """
        Validate that a file is a proper MP3 file using mutagen.
        
        Args:
            file_path: Path to the MP3 file
            
        Returns:
            Tuple of (is_valid, error_message)
            is_valid: True if file is a valid MP3
            error_message: None if valid, error description if invalid
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return False, f"File does not exist: {file_path}"
        
        if not self.is_mp3_file(file_path):
            return False, f"File does not have MP3 extension: {file_path}"
        
        try:
            # Try to load the file with mutagen
            audio_file = File(str(file_path))
            
            if audio_file is None:
                return False, f"File is not a valid audio file: {file_path}"
            
            if not isinstance(audio_file, MP3):
                return False, f"File is not a valid MP3 file: {file_path}"
            
            # Check if file has audio data
            if audio_file.info.length <= 0:
                return False, f"MP3 file appears to be empty or corrupted: {file_path}"
            
            return True, None
            
        except MutagenError as e:
            return False, f"Mutagen error reading file: {e}"
        except Exception as e:
            return False, f"Unexpected error validating file: {e}"
    
    def extract_metadata(self, file_path: Union[str, Path]) -> Dict[str, Optional[str]]:
        """
        Extract ID3 metadata from an MP3 file.
        
        Args:
            file_path: Path to the MP3 file
            
        Returns:
            Dictionary with metadata keys: artist, album, title, genre, year
            Returns None for missing metadata fields
        """
        file_path = Path(file_path)
        metadata = {
            'artist': None,
            'album': None,
            'title': None,
            'genre': None,
            'year': None
        }
        
        try:
            audio_file = MP3(str(file_path))
            
            # Extract common ID3 tags
            # TIT2 = Title, TPE1 = Artist, TALB = Album, TCON = Genre, TDRC/TYER = Year
            metadata['title'] = self._get_id3_text(audio_file, ['TIT2'])
            metadata['artist'] = self._get_id3_text(audio_file, ['TPE1'])
            metadata['album'] = self._get_id3_text(audio_file, ['TALB'])
            metadata['genre'] = self._get_id3_text(audio_file, ['TCON'])
            metadata['year'] = self._get_id3_text(audio_file, ['TDRC', 'TYER'])
            
            logger.debug(f"Extracted metadata from {file_path}: {metadata}")
            return metadata
            
        except ID3NoHeaderError:
            logger.warning(f"No ID3 header found in file: {file_path}")
            return metadata
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            return metadata
    
    def _get_id3_text(self, audio_file: MP3, tag_names: List[str]) -> Optional[str]:
        """
        Get text from ID3 tags, trying multiple tag names in order.
        
        Args:
            audio_file: MP3 file object
            tag_names: List of tag names to try
            
        Returns:
            Text content or None if not found
        """
        for tag_name in tag_names:
            try:
                if tag_name in audio_file.tags:
                    tag_value = audio_file.tags[tag_name]
                    if hasattr(tag_value, 'text') and tag_value.text:
                        # Return first text element, stripped of whitespace
                        return str(tag_value.text[0]).strip()
            except (AttributeError, IndexError, TypeError):
                continue
        return None
    
    def extract_artwork(self, file_path: Union[str, Path]) -> Optional[Dict[str, Union[bytes, str]]]:
        """
        Extract embedded artwork from an MP3 file.
        
        Args:
            file_path: Path to the MP3 file
            
        Returns:
            Dictionary with artwork data:
            {
                'data': bytes,          # Image data
                'mime': str,           # MIME type (image/jpeg, image/png)
                'type': int,           # APIC type (usually 3 for front cover)
                'description': str,    # Description text
                'size': int           # Size in bytes
            }
            Returns None if no artwork found
        """
        file_path = Path(file_path)
        
        try:
            audio_file = MP3(str(file_path))
            
            if not audio_file.tags:
                logger.debug(f"No ID3 tags found in file: {file_path}")
                return None
            
            # Look for APIC (Attached Picture) frames
            artwork_frames = [tag for tag in audio_file.tags.values() if isinstance(tag, APIC)]
            
            if not artwork_frames:
                logger.debug(f"No artwork found in file: {file_path}")
                return None
            
            # If multiple artwork frames, prioritize by type (3 = front cover)
            front_cover = None
            largest_artwork = None
            largest_size = 0
            
            for frame in artwork_frames:
                if frame.type == 3:  # Front cover
                    front_cover = frame
                    break
                
                # Track largest artwork as fallback
                if len(frame.data) > largest_size:
                    largest_artwork = frame
                    largest_size = len(frame.data)
            
            # Use front cover if available, otherwise largest artwork
            selected_frame = front_cover or largest_artwork
            
            if selected_frame:
                artwork_info = {
                    'data': selected_frame.data,
                    'mime': selected_frame.mime,
                    'type': selected_frame.type,
                    'description': selected_frame.desc,
                    'size': len(selected_frame.data)
                }
                
                logger.info(f"Extracted artwork from {file_path}: {artwork_info['mime']}, "
                           f"{artwork_info['size']} bytes, type {artwork_info['type']}")
                return artwork_info
            
            return None
            
        except ID3NoHeaderError:
            logger.debug(f"No ID3 header found in file: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error extracting artwork from {file_path}: {e}")
            return None
    
    def get_file_info(self, file_path: Union[str, Path]) -> Dict[str, Union[str, int, float, bool]]:
        """
        Get comprehensive information about an MP3 file.
        
        Args:
            file_path: Path to the MP3 file
            
        Returns:
            Dictionary with file information:
            {
                'path': str,
                'filename': str,
                'size_bytes': int,
                'is_valid': bool,
                'duration_seconds': float,
                'bitrate': int,
                'sample_rate': int,
                'has_artwork': bool,
                'metadata': dict,
                'error': str or None
            }
        """
        file_path = Path(file_path)
        
        info = {
            'path': str(file_path),
            'filename': file_path.name,
            'size_bytes': 0,
            'is_valid': False,
            'duration_seconds': 0.0,
            'bitrate': 0,
            'sample_rate': 0,
            'has_artwork': False,
            'metadata': {},
            'error': None
        }
        
        try:
            # Basic file info
            if file_path.exists():
                info['size_bytes'] = file_path.stat().st_size
            
            # Validate file
            is_valid, error = self.validate_mp3_file(file_path)
            info['is_valid'] = is_valid
            
            if not is_valid:
                info['error'] = error
                return info
            
            # Audio file info
            audio_file = MP3(str(file_path))
            info['duration_seconds'] = audio_file.info.length
            info['bitrate'] = audio_file.info.bitrate
            info['sample_rate'] = audio_file.info.sample_rate
            
            # Metadata
            info['metadata'] = self.extract_metadata(file_path)
            
            # Artwork check
            artwork = self.extract_artwork(file_path)
            info['has_artwork'] = artwork is not None
            
        except Exception as e:
            info['error'] = str(e)
            logger.error(f"Error getting file info for {file_path}: {e}")
        
        return info 