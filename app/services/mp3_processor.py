"""
MP3 Processing Service for MP3 Artwork Manager
Handles metadata extraction, artwork extraction, and MP3 file operations
"""
import os
import re
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, PictureType
from PIL import Image
from io import BytesIO
from flask import current_app
import tempfile


class MP3ProcessingError(Exception):
    """Custom exception for MP3 processing errors"""
    pass


class MP3Processor:
    """Service for processing MP3 files"""
    
    def __init__(self):
        self.supported_image_formats = ['JPEG', 'PNG']
    
    def extract_metadata(self, file_path):
        """
        Extract metadata from MP3 file including ID3 tags
        Returns dict with extracted metadata
        """
        try:
            # Load the MP3 file
            mp3_file = MP3(file_path, ID3=ID3)
            
            # Initialize metadata dict
            metadata = {
                'duration': 0,
                'bitrate': 0,
                'sample_rate': 0,
                'channels': 0,
                'title': None,
                'artist': None,
                'album': None,
                'has_id3': False,
                'id3_version': None
            }
            
            # Get audio properties
            if mp3_file.info:
                metadata.update({
                    'duration': mp3_file.info.length,
                    'bitrate': mp3_file.info.bitrate,
                    'sample_rate': mp3_file.info.sample_rate,
                    'channels': mp3_file.info.channels
                })
            
            # Get ID3 tags if available
            if mp3_file.tags:
                metadata['has_id3'] = True
                metadata['id3_version'] = str(mp3_file.tags.version)
                
                # Extract common tags
                if 'TIT2' in mp3_file.tags:  # Title
                    metadata['title'] = str(mp3_file.tags['TIT2'])
                
                if 'TPE1' in mp3_file.tags:  # Artist
                    metadata['artist'] = str(mp3_file.tags['TPE1'])
                
                if 'TALB' in mp3_file.tags:  # Album
                    metadata['album'] = str(mp3_file.tags['TALB'])
            
            current_app.logger.info(f"Extracted metadata for {os.path.basename(file_path)}: {metadata}")
            return metadata
            
        except Exception as e:
            error_msg = f"Failed to extract metadata from {file_path}: {str(e)}"
            current_app.logger.error(error_msg)
            raise MP3ProcessingError(error_msg)
    
    def parse_filename_metadata(self, filename):
        """
        Parse artist and title from filename as fallback
        Supports formats like "Artist - Title.mp3" or "Artist_-_Title.mp3"
        """
        try:
            # Remove file extension
            name_without_ext = os.path.splitext(filename)[0]
            
            # Common patterns for artist - title separation
            patterns = [
                r'^(.+?)\s*-\s*(.+)$',  # "Artist - Title"
                r'^(.+?)_-_(.+)$',      # "Artist_-_Title" 
                r'^(.+?)\s*–\s*(.+)$',  # "Artist – Title" (em dash)
                r'^(.+?)\s*—\s*(.+)$',  # "Artist — Title" (em dash)
            ]
            
            for pattern in patterns:
                match = re.match(pattern, name_without_ext)
                if match:
                    artist = match.group(1).strip()
                    title = match.group(2).strip()
                    
                    # Basic cleanup
                    artist = re.sub(r'[_]+', ' ', artist).strip()
                    title = re.sub(r'[_]+', ' ', title).strip()
                    
                    current_app.logger.info(f"Parsed filename '{filename}' -> Artist: '{artist}', Title: '{title}'")
                    return {'artist': artist, 'title': title}
            
            # If no pattern matches, use the whole filename as title
            current_app.logger.warning(f"Could not parse artist/title from filename: {filename}")
            return {'artist': None, 'title': name_without_ext}
            
        except Exception as e:
            current_app.logger.error(f"Error parsing filename {filename}: {str(e)}")
            return {'artist': None, 'title': filename}
    
    def extract_embedded_artwork(self, file_path):
        """
        Extract embedded artwork from MP3 file
        Returns list of artwork dictionaries
        """
        try:
            mp3_file = MP3(file_path, ID3=ID3)
            artwork_list = []
            
            if not mp3_file.tags:
                current_app.logger.info(f"No ID3 tags found in {file_path}")
                return artwork_list
            
            # Look for APIC frames (attached pictures)
            apic_frames = mp3_file.tags.getall('APIC')
            
            for i, apic in enumerate(apic_frames):
                try:
                    # Create temporary file for the artwork
                    temp_file = tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=f'_embedded_{i}.jpg',
                        dir=current_app.config['TEMP_FOLDER']
                    )
                    
                    # Write image data
                    temp_file.write(apic.data)
                    temp_file.close()
                    
                    # Get image info using PIL
                    with Image.open(temp_file.name) as img:
                        width, height = img.size
                        format_name = img.format
                    
                    # Get file size
                    file_size = len(apic.data)
                    
                    artwork_info = {
                        'source': 'embedded',
                        'image_path': temp_file.name,
                        'dimensions': {'width': width, 'height': height},
                        'file_size': file_size,
                        'format': format_name,
                        'mime_type': apic.mime,
                        'picture_type': apic.type,
                        'description': apic.desc,
                        'index': i
                    }
                    
                    artwork_list.append(artwork_info)
                    current_app.logger.info(f"Extracted embedded artwork {i}: {width}x{height} {format_name}, {file_size} bytes")
                    
                except Exception as e:
                    current_app.logger.error(f"Error extracting embedded artwork {i}: {str(e)}")
                    # Clean up temp file if it was created
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass
            
            current_app.logger.info(f"Found {len(artwork_list)} embedded artwork(s) in {file_path}")
            return artwork_list
            
        except Exception as e:
            error_msg = f"Failed to extract embedded artwork from {file_path}: {str(e)}"
            current_app.logger.error(error_msg)
            raise MP3ProcessingError(error_msg)
    
    def get_search_terms(self, file_path, filename):
        """
        Get search terms for MusicBrainz API
        First tries ID3 tags, falls back to filename parsing
        """
        try:
            # Extract metadata first
            metadata = self.extract_metadata(file_path)
            
            # Use ID3 tags if available
            if metadata.get('artist') and metadata.get('title'):
                return {
                    'artist': metadata['artist'],
                    'title': metadata['title'],
                    'album': metadata.get('album'),
                    'source': 'id3_tags'
                }
            
            # Fall back to filename parsing
            parsed = self.parse_filename_metadata(filename)
            return {
                'artist': parsed.get('artist'),
                'title': parsed.get('title'),
                'album': None,
                'source': 'filename_parsing'
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting search terms for {file_path}: {str(e)}")
            return {
                'artist': None,
                'title': os.path.splitext(filename)[0],
                'album': None,
                'source': 'fallback'
            }
    
    def embed_artwork(self, mp3_file_path, artwork_path, output_path):
        """
        Embed artwork into MP3 file and save to output path
        Preserves all existing metadata except artwork
        """
        try:
            # Load the original MP3 file
            mp3_file = MP3(mp3_file_path, ID3=ID3)
            
            # Create ID3 tags if they don't exist
            if mp3_file.tags is None:
                mp3_file.add_tags()
            
            # Remove existing artwork
            mp3_file.tags.delall('APIC')
            
            # Load and prepare new artwork
            with open(artwork_path, 'rb') as artwork_file:
                artwork_data = artwork_file.read()
            
            # Determine MIME type based on file extension
            artwork_ext = os.path.splitext(artwork_path)[1].lower()
            if artwork_ext in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            elif artwork_ext == '.png':
                mime_type = 'image/png'
            else:
                raise MP3ProcessingError(f"Unsupported artwork format: {artwork_ext}")
            
            # Create APIC frame for front cover
            apic = APIC(
                encoding=3,  # UTF-8
                mime=mime_type,
                type=PictureType.COVER_FRONT,
                desc='Cover',
                data=artwork_data
            )
            
            # Add the artwork
            mp3_file.tags.add(apic)
            
            # Save to output path
            mp3_file.save(output_path)
            
            current_app.logger.info(f"Successfully embedded artwork in {output_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to embed artwork: {str(e)}"
            current_app.logger.error(error_msg)
            raise MP3ProcessingError(error_msg)
    
    def copy_with_new_artwork(self, source_path, artwork_path, output_path, preserve_filename=True):
        """
        Create a copy of the MP3 file with new artwork embedded
        Preserves original filename exactly if preserve_filename is True
        """
        try:
            # First, copy the file to preserve everything
            import shutil
            shutil.copy2(source_path, output_path)
            
            # Then embed the new artwork
            self.embed_artwork(output_path, artwork_path, output_path)
            
            current_app.logger.info(f"Created MP3 copy with new artwork: {output_path}")
            return output_path
            
        except Exception as e:
            error_msg = f"Failed to create MP3 copy with artwork: {str(e)}"
            current_app.logger.error(error_msg)
            # Clean up partial file if it exists
            try:
                if os.path.exists(output_path):
                    os.unlink(output_path)
            except:
                pass
            raise MP3ProcessingError(error_msg)
    
    def validate_mp3_file(self, file_path):
        """
        Validate that the file is a proper MP3 file
        """
        try:
            mp3_file = MP3(file_path)
            if mp3_file.info is None:
                raise MP3ProcessingError("File is not a valid MP3")
            return True
        except Exception as e:
            raise MP3ProcessingError(f"MP3 validation failed: {str(e)}")
    
    def get_mp3_info_summary(self, file_path):
        """
        Get a summary of MP3 file information for display
        """
        try:
            metadata = self.extract_metadata(file_path)
            embedded_artwork = self.extract_embedded_artwork(file_path)
            
            # Format duration
            duration = metadata.get('duration', 0)
            duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}" if duration else "Unknown"
            
            return {
                'metadata': metadata,
                'embedded_artwork_count': len(embedded_artwork),
                'duration_formatted': duration_str,
                'file_size': os.path.getsize(file_path),
                'has_artwork': len(embedded_artwork) > 0
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting MP3 info for {file_path}: {str(e)}")
            return {
                'metadata': {},
                'embedded_artwork_count': 0,
                'duration_formatted': "Unknown",
                'file_size': 0,
                'has_artwork': False,
                'error': str(e)
            }
